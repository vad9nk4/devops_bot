import logging
import re
import os

from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import psycopg2
from psycopg2 import Error
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение значений переменных окружения
HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")

# Получение значений переменных окружения для БД.
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT")
DATABASE = os.getenv("DATABASE")

TOKEN = str(os.getenv("TOKEN"))

# Подключаем логирование
logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')


def helpCommand(update: Update, context):
    update.message.reply_text('Help!')

def ssh_command(command):
    import paramiko

    # Создание SSH-клиента
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Подключение к удаленному серверу
        client.connect(hostname=HOST, username=USER, password=PASSWORD, port=PORT)

        # Выполнение команды на удаленном сервере
        stdin, stdout, stderr = client.exec_command(command)

        # Получение результатов выполнения команды
        result = stdout.read().decode('utf-8')

    except Exception as e:
        result = str(e)

    finally:
        # Закрытие соединения с удаленным сервером
        client.close()

    return result


def get_data_from_database(update: Update, context, query):
    try:
        # Устанавливаем соединение с базой данных
        with psycopg2.connect(user=DB_USER,
                              password=DB_PASS,
                              host=HOST,
                              port=DB_PORT,
                              database=DATABASE) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                data = cursor.fetchall()

                if data:
                    # Если есть данные, отправляем их пользователю
                    formatted_data = '\n'.join([f'{i+1}. {row[0]}' for i, row in enumerate(data)])
                    update.message.reply_text(formatted_data)
                else:
                    # Если данных нет, отправляем сообщение об этом
                    update.message.reply_text("Данные не найдены.")

    except (Exception, Error) as error:
        # В случае ошибки отправляем сообщение об ошибке
        update.message.reply_text(f"Произошла ошибка при выполнении запроса: {error}")

# Обработчик команды для получения email-адресовs
def get_emails(update: Update, context):
    query = "SELECT email FROM emails;"
    get_data_from_database(update, context, query)

# Обработчик команды для получения номеров телефона
def get_phone_numbers(update: Update, context):
    query = "SELECT phone_number FROM phone_numbers;"
    get_data_from_database(update, context, query)


def get_repl_logs(update: Update, context):
    # Отправляем сообщение о выполнении команды
    update.message.reply_text("Ищу логи о репликации...")
    
    # Вызываем функцию ssh_command для выполнения команды на удаленном сервере
    repl_logs_info = ssh_command("cat /var/log/postgresql/postgresql-14-main.log | grep repl")
    
    # Отправляем найденные логи в сообщении
    if len(repl_logs_info) > 4096:
        update.message.reply_text(repl_logs_info[:4096])
    else:
        update.message.reply_text(repl_logs_info)

def get_release(update: Update, context):
    release_info = ssh_command("lsb_release -a")
    update.message.reply_text(release_info)

def get_uname(update: Update, context):
    uname_info = ssh_command("uname -a")
    update.message.reply_text(uname_info)

def get_uptime(update: Update, context):
    uptime_info = ssh_command("uptime")
    update.message.reply_text(uptime_info)

def get_df(update: Update, context):
    df_info = ssh_command("df -h")
    update.message.reply_text(df_info)

def get_free(update: Update, context):
    free_info = ssh_command("free -h")
    update.message.reply_text(free_info)

def get_mpstat(update: Update, context):
    mpstat_info = ssh_command("mpstat")
    update.message.reply_text(mpstat_info)

def get_w(update: Update, context):
    w_info = ssh_command("w")
    update.message.reply_text(w_info)

def get_auths(update: Update, context):
    auths_info = ssh_command("last -n 10")
    update.message.reply_text(auths_info)

def get_critical(update: Update, context):
    critical_info = ssh_command("journalctl -n 5 -p crit")
    update.message.reply_text(critical_info)

def get_ps(update: Update, context):
    ps_info = ssh_command("ps aux | head -n 30")
    update.message.reply_text(ps_info)

def get_ss(update: Update, context):
    ss_info = ssh_command("ss -tuln")
    update.message.reply_text(ss_info)


# Стоит учесть два варианта взаимодействия с этой командой:
    #1. Вывод всех пакетов;
    #2. Поиск информации о пакете, название которого будет запрошено у пользователя.
# Определение состояний для обработки команды /get_apt_list
CHOOSING_ACTION, SEARCHING_PACKAGE = range(2)

# Функция для обработки команды /get_apt_list
def get_apt_list(update: Update, context):
    # Отправляем пользователю сообщение с вариантами действий
    update.message.reply_text(
        "❗ Выберите действие:\n"
        "1. Вывести все пакеты\n"
        "2. Поиск информации о пакете\n"
        "Отправьте соответствующую цифру."
    )

    # Переходим в состояние CHOOSING_ACTION
    return 'choose_action'

# Функция для обработки ответа пользователя на выбор действия
def choose_action(update: Update, context):
    # Получаем выбранный пользователем вариант действия
    action = update.message.text

    if action == "1":
        # Если пользователь выбрал вывод всех пакетов, отправляем соответствующий ответ
        apt_list_info = ssh_command("dpkg -l")
        # Отправить только первые 4096 символов
        if len(apt_list_info) > 4096:
            update.message.reply_text(apt_list_info[:4096])
        else:
            update.message.reply_text(apt_list_info)
        return ConversationHandler.END
    elif action == "2":
        # Если пользователь выбрал поиск информации о пакете, переходим в состояние SEARCHING_PACKAGE
        update.message.reply_text("Введите название пакета для поиска:")
        return 'search_package'
    else:
        # Если введенное значение некорректно, предлагаем выбрать действие снова
        update.message.reply_text("Пожалуйста, выберите действие, отправив соответствующую цифру.")
        return 'choose_action'

# Функция для обработки запроса информации о конкретном пакете
def search_package(update: Update, context):
    package_name = update.message.text

    # Выполняем поиск информации о пакете
    apt_package_info = ssh_command(f"dpkg -l | grep {package_name}")
    
    if not apt_package_info.strip():
        update.message.reply_text("Ничего не найдено.")
    else:
        if len(apt_package_info) > 4096:
            update.message.reply_text(apt_package_info[:4096])
        else:
            update.message.reply_text(apt_package_info)

    return ConversationHandler.END


def get_services(update: Update, context):
    # Выполнить команду systemctl на удаленном сервере
    services_info = ssh_command("systemctl list-units --type=service --state=running")

    # Отправить информацию о сервисах пользователю
    update.message.reply_text(services_info)


def verify_passwordCommand(update: Update, context):
    update.message.reply_text('Введите ваш пароль для проверки сложности')

    return 'verify_password'

def verify_password(update: Update, context):
    user_input = update.message.text

    passwordRegex = re.compile(r'^(?=.*\d)(?=.*[a-zA-Z])(?=.*[A-Z])(?=.*[!\@\#\$\%\^\&\*\(\)\])(?=.*[a-zA-Z]).{8,}$')

    if passwordRegex.match(user_input):
        update.message.reply_text('Пароль сложный')
    else:
        update.message.reply_text('Пароль простой')
    
    return ConversationHandler.END

def connect_to_database():
    try:
        connection = psycopg2.connect(
            user=DB_USER,
            password=DB_PASS,
            host=HOST,
            port=DB_PORT,
            database=DATABASE
        )
        return connection
    except (Exception, Error) as error:
        logger.error(f"Error while connecting to PostgreSQL: {error}")
        return None

def findEmailCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска Email-адреса')

    return 'findEmail'


def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')

    return 'findPhoneNumbers'

def findEmail(update: Update, context):
    user_input = update.message.text
    emailRegex = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
    emailList = emailRegex.findall(user_input)

    if not emailList:
        update.message.reply_text('Email-адреса не были найдены')
        return ConversationHandler.END

    emails = ''
    for i, email in enumerate(emailList):
        emails += f'{i+1}. {email}\n'

    update.message.reply_text(emails)

    # Save each email address individually
    for email in emailList:
        context.user_data.setdefault('emails', []).append(email)

    # Ask user if they want to save the found email addresses
    update.message.reply_text('Хотите сохранить найденные email-адреса в базе данных? Ответьте "Да" или "Нет".')

    # Move to the next state to handle user's response
    return 'save_emails'


def save_emails(update: Update, context):
    user_input = update.message.text.lower()

    # Check if user wants to save the found email addresses
    if user_input == 'Да' or user_input == 'да':
        connection = connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                # Get the found email addresses
                emails = context.user_data.get('emails', [])
                # Insert each email address into the database
                for email in emails:
                    cursor.execute("INSERT INTO emails (email) VALUES (%s);", (email,))
                connection.commit()
                update.message.reply_text('Email-адреса успешно сохранены в базе данных.')
            except (Exception, Error) as error:
                logger.error(f"Error while inserting email addresses into the database: {error}")
                update.message.reply_text('Произошла ошибка при сохранении email-адресов в базу данных.')
            finally:
                cursor.close()
                connection.close()
        else:
            update.message.reply_text('Не удалось подключиться к базе данных. Пожалуйста, попробуйте позже.')
    else:
        update.message.reply_text('Email-адреса не будут сохранены в базе данных.')

    return ConversationHandler.END


def findPhoneNumbers(update: Update, context):
    user_input = update.message.text
    phoneNumRegex = re.compile(r'(?:\+7|8)[ -]?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}')
    phoneNumberList = phoneNumRegex.findall(user_input)

    if not phoneNumberList:
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END

    phone_numbers = ''
    for i, number in enumerate(phoneNumberList):
        phone_numbers += f'{i+1}. {number}\n'

    update.message.reply_text(phone_numbers)

    # Save each phone number individually
    for number in phoneNumberList:
        context.user_data.setdefault('phone_numbers', []).append(number)

    # Ask user if they want to save the found phone numbers
    update.message.reply_text('Хотите сохранить найденные телефонные номера в базе данных? Ответьте "Да" или "Нет".')

    # Move to the next state to handle user's response
    return 'save_phone_numbers'


def save_phone_numbers(update: Update, context):
    user_input = update.message.text.lower()

    # Check if user wants to save the found phone numbers
    if user_input == 'Да' or user_input == 'да':
        connection = connect_to_database()
        if connection:
            try:
                cursor = connection.cursor()
                # Get the found phone numbers
                phone_numbers = context.user_data.get('phone_numbers', [])
                # Insert each phone number into the database
                for number in phone_numbers:
                    cursor.execute("INSERT INTO phone_numbers (phone_number) VALUES (%s);", (number, ))
                connection.commit()
                update.message.reply_text('Телефонные номера успешно сохранены в базе данных.')
            except (Exception, Error) as error:
                logger.error(f"Error while inserting phone numbers into the database: {error}")
                update.message.reply_text('Произошла ошибка при сохранении телефонных номеров в базе данных.')
            finally:
                cursor.close()
                connection.close()
        else:
            update.message.reply_text('Не удалось подключиться к базе данных. Пожалуйста, попробуйте позже.')
    else:
        update.message.reply_text('Телефонные номера не будут сохранены в базе данных.')

    return ConversationHandler.END



def echo(update: Update, context):
    update.message.reply_text(update.message.text)


def main():
    updater = Updater(TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher


    # Обработчик диалога
    convHandlerCheckPassComplex = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verify_passwordCommand)],
        states={
            'verify_password': [MessageHandler(Filters.text & ~Filters.command, verify_password)],
        },
        fallbacks=[]
    )


    convHandlerFindEmail = ConversationHandler(
        entry_points=[CommandHandler('findEmail', findEmailCommand)],
        states={
            'findEmail': [MessageHandler(Filters.text & ~Filters.command, findEmail)],
            'save_emails': [MessageHandler(Filters.text & ~Filters.command, save_emails)],
        },
        fallbacks=[]
    )

    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('findPhoneNumbers', findPhoneNumbersCommand)],
        states={
            'findPhoneNumbers': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            'save_phone_numbers': [MessageHandler(Filters.text & ~Filters.command, save_phone_numbers)],
        },
        fallbacks=[]
    )

    # Определение состояний и обработчиков для команды /get_apt_list
    convHandlerGetAptList = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', get_apt_list)],
        states={
            'choose_action': [MessageHandler(Filters.text & ~Filters.command, choose_action)],
            'search_package': [MessageHandler(Filters.text & ~Filters.command, search_package)],
        },
        fallbacks=[]
    )

  	
	# Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))
    dp.add_handler(convHandlerCheckPassComplex)
    dp.add_handler(convHandlerFindEmail)
    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(convHandlerGetAptList)



    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_services", get_services))
    dp.add_handler(CommandHandler("get_apt_list", get_apt_list))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))

    # Регистрация обработчиков команд для вывода данных из БД.
    dp.add_handler(CommandHandler("get_emails", get_emails))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))

	# Регистрируем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
		
	# Запускаем бота
    updater.start_polling()

	# Останавливаем бота при нажатии Ctrl+C
    updater.idle()


if __name__ == '__main__':
    main()

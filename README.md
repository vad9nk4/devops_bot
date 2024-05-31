# devops_bot

secrets.yml must be specified!!! (look example)\
version of postgresql: postgresql-14\
bot.py from main branch specified to work with postgresql-14 ( get_repl_logs )\
\
start command: ansible-playbook -i inventory/hosts --extra-vars "@secrets.yml" playbook_tg_bot.yml

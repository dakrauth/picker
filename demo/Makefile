init:
	rm -f db.sqlite3 > /dev/null 2>&1
	./manage.py migrate
	./manage.py loaddemo
	@echo

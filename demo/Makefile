init:
	pip install -U -r requirements.txt
	rm -f db.sqlite3 > /dev/null 2>&1
	./manage.py migrate
	./manage.py loaddata nfl_demo_data
	@echo

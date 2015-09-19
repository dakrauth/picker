init:
	pip install -U -r requirements.txt
	rm db.sqlite3
	./manage.py migrate
	./manage.py loaddata nfl_teams nfl_demo_data
	@echo

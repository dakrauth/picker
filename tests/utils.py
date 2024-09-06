def export_db(filename="dump.sql"):
    from django.db import connections

    connection = connections["default"].connection
    with open(filename, "w") as fp:
        for line in connection.iterdump():
            fp.write("{}\n".format(line))

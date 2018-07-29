Picker
======

A Django-based sports picker app for various leagues.

Templates
---------

The default, included templates are all `Bootstrap 3 <http://getbootstrap.com/>`_ based.

Demo
----

For Linux/Mac OS X:

.. code-block:: bash

    $ git clone https://github.com/dakrauth/picker.git
    $ cd picker
    $ python -m venv venv
    $ pip install -r requirements.txt
    $ pip install -e .
    $ pip install -e demo
    $ demo migrate
    $ demo loaddemo
    $ demo runserver

Browse to: http://127.0.0.1:8000

User ``demo``, password ``demo`` has management rights. Users [``user1``, ``user2``, ..., ``user9``]
all share password ``password``.

Meta
----

Distributed under the MIT License, see ``LICENSE`` file for more information.

https://github.com/dakrauth/picker

import os
from invoke import task

PYWARN='python -Wd'

@task
def rmdb(ctx):
    ctx.run('rm -f demo/db.sqlite3')


@task
def clean(ctx):
    '''Remove build artifacts'''
    rmdb(ctx)
    ctx.run('rm -rf __pycache__ .cache build picker.egg-info demo/demo.egg-info .coverage')


@task
def install(ctx):
    '''Install base requirements'''
    ctx.run('pip install -r requirements.txt', pty=True)


@task
def test(ctx, cov=False):
    '''Run tests and coverage. Optionally open the coverage reports.'''
    cov_string = ''
    if cov:
        cov_string = '--cov-config .coveragerc --cov-report html --cov-report term --cov=picker'

    ctx.run("py.test {}".format(cov_string), pty=True)

    if cov and os.path.exists('build/coverage/index.html'):
        ctx.run('open build/coverage/index.html', pty=True)


@task
def demo(ctx, reset=False):
    '''Set up the demo environment and run the server'''
    if reset:
        rmdb(ctx)

    ctx.run('demo check', pty=True)
    ctx.run('demo loaddemo', pty=True)
    ctx.run('demo runserver', pty=True)


@task
def check(ctx):
    '''Run PEP8 checks'''
    ctx.run('pycodestyle picker')


VERSION = (0, 2, 1)
default_app_config = 'picker.apps.PickerConfig'


def get_version():
    return '.'.join(map(str, VERSION))

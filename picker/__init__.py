VERSION = (2, 2, 0)
default_app_config = "picker.apps.PickerConfig"


def get_version():
    return ".".join(map(str, VERSION))

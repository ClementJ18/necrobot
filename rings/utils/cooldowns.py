from discord.ext.commands.cooldowns import BucketType


def _small_cooldown():
    return 5, 1


def _medium_cooldown():
    return 3, 3


def _long_cooldown():
    return 1, 5


def _small_user():
    return _small_cooldown(), BucketType.user


def _medium_user():
    return _medium_cooldown(), BucketType.user


def _long_user():
    return _long_cooldown(), BucketType.user


def _small_channel():
    return _small_cooldown(), BucketType.channel


def _medium_channel():
    return _medium_cooldown(), BucketType.channel


def _long_channel():
    return _long_cooldown(), BucketType.channel


def _small_server():
    return _small_cooldown(), BucketType.server


def _medium_server():
    return _medium_cooldown(), BucketType.server


def _long_server():
    return _long_cooldown(), BucketType.server

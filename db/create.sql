CREATE TABLE necrobot.Users (
    user_id bigint PRIMARY KEY,
    necroins int,
    exp int,
    daily char(10),
    badges varchar(4000),
    title varchar(40),
    tutorial varchar(5) DEFAULT 'False'
);

CREATE TABLE necrobot.Guilds (
    guild_id bigint PRIMARY KEY,
    mute bigint,
    automod_channel bigint,
    welcome_channel bigint,
    welcome_message varchar(2000),
    goodbye_message varchar(2000),
    prefix varchar(2000),
    broadcast_channel bigint,
    broadcast_message varchar(2000),
    broadcast_time int,
    starboard_channel bigint,
    starboard_limit int,
    auto_role bigint,
    auto_role_timer int,
);

CREATE TABLE necrobot.Disabled (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    command varchar(50),
    PRIMARY KEY (guild_id, command)
);

CREATE TABLE necrobot.IgnoreAutomod (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    id bigint,
    PRIMARY KEY(guild_id, id)
);

CREATE TABLE necrobot.IgnoreCommand (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    id bigint,
    PRIMARY KEY(guild_id, id)
);

CREATE TABLE necrobot.SelfRoles (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    id bigint,
    PRIMARY KEY(guild_id, id)
);

CREATE TABLE necrobot.Tags (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    name varchar(2000),
    content varchar(2000),
    owner_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    uses int,
    created_at varchar(1000),
    PRIMARY KEY(guild_id, name)
);

CREATE TABLE necrobot.Permissions (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    level int,
    PRIMARY KEY(guild_id, user_id)
);

CREATE TABLE necrobot.Badges (
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    place int,
    badge varchar(40),
    PRIMARY KEY(user_id, place)
);

CREATE TABLE necrobot.Gifts (
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    gift varchar(40),
    amount int,
    PRIMARY KEY(user_id, guild_id, gift)
);

CREATE TABLE necrobot.Waifus (
    user_id bigint  REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    waifu_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    PRIMARY KEY(user_id, guild_id, waifu_id)
);

CREATE TABLE necrobot.Waifu (
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    value int,
    claimer_id bigint,
    affinity_id bigint,
    heart_changes int,
    divorces int,
    flowers int,
    PRIMARY KEY(user_id, guild_id)
);

CREATE TABLE necrobot.Logs(
    log_id serial PRIMARY KEY,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    username varchar(40),
    command varchar(50),
    guild_id bigint,
    guildname varchar(40),
    message varchar(2000),
    time_used timestamp DEFAULT localtimestamp,
    can_run varchar(5)
);

CREATE TABLE necrobot.Warnings(
    warn_id serial PRIMARY KEY,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    issuer_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    warning_content varchar(2000),
    date_issued varchar(100)
);

CREATE TABLE necrobot.Starred(
    message_id bigint PRIMARY KEY,
    starred_id bigint,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE
);

CREATE TABLE necrobot.Aliases(
    alias varchar(2000),
    original varchar(2000),
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    PRIMARY KEY(alias, original, guild_id)
);

CREATE TABLE necrobot.Reminders(
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    channel_id bigint,
    reminder varchar(2000),
    timer varchar(200),
    start_date varchar(200),
    PRIMARY KEY(user_id, start_date)
);

CREATE TABLE necrobot.Polls(
    message_id bigint PRIMARY KEY,
    votes int 
);

CREATE TABLE necrobot.Votes(
    message_id bigint REFERENCES necrobot.Polls(message_id) ON DELETE CASCADE,
    user_id bigint,
    reaction varchar(200)
);

CREATE TABLE necrobot.Modio(
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    game_id bigint,
    PRIMARY KEY(user_id, guild_id)
);

CREATE TABLE necrobot.Youtube(
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    channel_id bigint,
    youtuber_id varchar(50),
    last_update TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    filter varchar(200),
    PRIMARY KEY(guild_id, youtuber_id)
);

CREATE TABLE necrobot.Invites(
    id varchar(10) PRIMARY KEY,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    url varchar(200),
    uses int,
    inviter bigint
);

CREATE TABLE necrobot.MU(
    id bigint PRIMARY KEY,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    thread varchar(500),
    message varchar(20000),
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE
);

CREATE TABLE necrobot.MU_Users(
    id bigint PRIMARY KEY REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    username varchar(200),
    username_lower varchar(200) UNIQUE
);

CREATE TABLE necrobot.Leaderboards(
    id bigint PRIMARY KEY REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    message varchar(200),
    symbol varchar(10)
);

CREATE TABLE necrobot.LeaderboardPoints(
    id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    board bigint REFERENCES necrobot.Guilds(guild_id),
    points bigint,
    PRIMARY KEY(id, board) 
);

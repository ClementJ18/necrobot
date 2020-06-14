CREATE TABLE necrobot.Users (
    user_id bigint PRIMARY KEY,
    necroins bigint CHECK (necroins >= 0) DEFAULT 200,
    exp int DEFAULT 0,
    daily date DEFAULT current_date,
    title varchar(40) DEFAULT '',
    tutorial int DEFAULT 0
);

CREATE TABLE necrobot.Guilds (
    guild_id bigint PRIMARY KEY,
    mute bigint DEFAULT 0,
    automod_channel bigint DEFAULT 0,
    welcome_channel bigint DEFAULT 0,
    welcome_message varchar(2000) DEFAULT '',
    goodbye_message varchar(2000) DEFAULT '',
    prefix varchar(2000) DEFAULT '',
    broadcast_channel bigint DEFAULT 0,
    broadcast_message varchar(2000) DEFAULT '',
    broadcast_time int DEFAULT 1,
    starboard_channel bigint DEFAULT 0,
    starboard_limit int DEFAULT 5 CHECK(starboard_limit > 0),
    auto_role bigint DEFAULT 0,
    auto_role_timer int DEFAULT 0
    pm_warning BOOLEAN DEFAULT False
);

CREATE TABLE necrobot.Permissions (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    level int CHECK(level BETWEEN 0 AND 7),
    PRIMARY KEY(guild_id, user_id)
);

CREATE TABLE necrobot.BadgeShop (
    name varchar(50) PRIMARY KEY,
    file_name varchar(55),
    cost int DEFAULT 0,
    special boolean DEFAULT FALSE
);

CREATE TABLE necrobot.Badges (
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    badge varchar(50) REFERENCES necrobot.BadgeShop(name) ON DELETE CASCADE,
    spot int DEFAULT 0 CHECK(spot BETWEEN 0 AND 8),
    PRIMARY KEY(user_id, badge),
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
    uses int DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY(guild_id, name)
);

CREATE TABLE necrobot.Aliases(
    alias varchar(2000),
    original varchar(2000),
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    PRIMARY KEY(alias, guild_id),
    FOREIGN KEY (original, guild_id) REFERENCES necrobot.Tags(name, guild_id) ON DELETE CASCADE
);

CREATE TABLE necrobot.Logs(
    log_id serial PRIMARY KEY,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    username varchar(40),
    command varchar(50),
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    guildname varchar(40),
    message varchar(2000),
    time_used TIMESTAMPTZ DEFAULT NOW(),
    can_run BOOLEAN DEFAULT TRUE
);

CREATE TABLE necrobot.Warnings(
    warn_id serial PRIMARY KEY,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    issuer_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    warning_content varchar(2000),
    date_issued TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE necrobot.Starred(
    message_id bigint PRIMARY KEY,
    starred_id bigint,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE
);

CREATE TABLE necrobot.Reminders(
    id SERIAL PRIMARY KEY,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    channel_id bigint,
    reminder varchar(2000),
    timer varchar(200),
    start_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE necrobot.Polls(
    message_id bigint PRIMARY KEY,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    link varchar(500),
    votes int CHECK(votes BETWEEN 1 AND 20)
);

CREATE TABLE necrobot.Votes(
    message_id bigint REFERENCES necrobot.Polls(message_id) ON DELETE CASCADE,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    reaction varchar(200), 
    PRIMARY KEY(message_id, user_id, reaction)
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
    user_id bigint,
    url varchar(500),
    apporver bigint
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE
    post_date date DEFAULT current_date, 
);

CREATE TABLE necrobot.MU_Users(
    user_id bigint PRIMARY KEY REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    username varchar(200),
    username_lower varchar(200) UNIQUE
);

CREATE TABLE necrobot.Leaderboards(
    guild_id bigint PRIMARY KEY REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    message varchar(200),
    symbol varchar(50)
);

CREATE TABLE necrobot.LeaderboardPoints(
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    points bigint,
    PRIMARY KEY(user_id, guild_id) 
);

CREATE TYPE channel_filter_hybrid as (
    channel_id bigint,
    filter varchar(50)
);

CREATE TYPE emote_count_hybrid as (
    reaction varchar(200),
    count int
);

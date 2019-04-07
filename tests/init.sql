CREATE DATABASE TS;
USE TS;

CREATE TABLE Person
(
    username  VARCHAR(20),
    password  VARCHAR(128),
    fname     VARCHAR(20),
    lname     VARCHAR(20),
    avatar    VARCHAR(2048),
    bio       VARCHAR(1024),
    isPrivate Boolean,
    PRIMARY KEY (username)
);

CREATE TABLE Photo
(
    photoID      int NOT NULL AUTO_INCREMENT,
    photoOwner   VARCHAR(20),
    timestamp    Timestamp,
    filePath     VARCHAR(2048),
    caption      VARCHAR(1024),
    allFollowers Boolean,
    PRIMARY KEY (photoID),
    FOREIGN KEY (photoOwner) REFERENCES Person (username) ON DELETE CASCADE
);

CREATE TABLE Follow
(
    followerUsername VARCHAR(20),
    followeeUsername VARCHAR(20),
    acceptedfollow   Boolean,
    PRIMARY KEY (followerUsername, followeeUsername),
    FOREIGN KEY (followerUsername) REFERENCES Person (username) ON DELETE CASCADE,
    FOREIGN KEY (followeeUsername) REFERENCES Person (username) ON DELETE CASCADE
);

CREATE TABLE CloseFriendGroup
(
    groupName  VARCHAR(20),
    groupOwner VARCHAR(20),
    PRIMARY KEY (groupName, groupOwner),
    FOREIGN KEY (groupOwner) REFERENCES Person (username) ON DELETE CASCADE
);

CREATE TABLE Belong
(
    groupName  VARCHAR(20),
    groupOwner VARCHAR(20),
    username   VARCHAR(20),
    PRIMARY KEY (groupName, groupOwner, username),
    FOREIGN KEY (groupName, groupOwner) REFERENCES CloseFriendGroup (groupName, groupOwner) ON DELETE CASCADE,
    FOREIGN KEY (username) REFERENCES Person (username) ON DELETE CASCADE
);

CREATE TABLE Share
(
    groupName  VARCHAR(20),
    groupOwner VARCHAR(20),
    photoID    int,
    PRIMARY KEY (groupName, groupOwner, photoID),
    FOREIGN KEY (groupName, groupOwner) REFERENCES CloseFriendGroup (groupName, groupOwner) ON DELETE CASCADE,
    FOREIGN KEY (photoID) REFERENCES Photo (photoID) ON DELETE CASCADE
);

CREATE TABLE Liked
(
    username  VARCHAR(20),
    photoID   int,
    timestamp Timestamp,
    PRIMARY KEY (username, photoID),
    FOREIGN KEY (username) REFERENCES Person (username) ON DELETE CASCADE,
    FOREIGN KEY (photoID) REFERENCES Photo (photoID) ON DELETE CASCADE
);

CREATE TABLE Tag
(
    username    VARCHAR(20),
    photoID     int,
    acceptedTag Boolean,
    PRIMARY KEY (username, photoID),
    FOREIGN KEY (username) REFERENCES Person (username) ON DELETE CASCADE,
    FOREIGN KEY (photoID) REFERENCES Photo (photoID) ON DELETE CASCADE
);

CREATE TABLE Comment
(
    username    VARCHAR(20),
    photoID     int,
    commentText VARCHAR(1024),
    timestamp   Timestamp,
    PRIMARY KEY (photoID, username),
    FOREIGN KEY (photoID) REFERENCES Photo (photoID) ON DELETE CASCADE,
    FOREIGN KEY (username) REFERENCES Person (username) ON DELETE CASCADE
);

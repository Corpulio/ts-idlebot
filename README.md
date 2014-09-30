ts-idlebot
==========

Command-line script to automatically move Teamspeak 3 users to a different channel when they go idle.

Usage: python ts-idlebot.py <<config file>>

Copy the ts-idlebot.conf.example file to ts-idlebot.conf and then set it up for your own server. You'll need a user with ServerQuery privileges - the easiest one to use here is probably the "serveradmin" username that gets configured when you first set up the server. If you're using a hosted TS server, you'll have to either use the ServerQuery username/password provided by your host, or ask them to configure you one.

.. role:: python(code)
    :language: python

=================
appset
=================

The following commands are part of the appset group.
They should be ran like ``[p]appset <command> <args>``

^^^^^^^^^^
channel [discord.TextChannel]
^^^^^^^^^^

The most basic command. Specify the channel applications go to when members apply.
Leave blank to clear and stop applications

Checks: ``Admin or Manage Server``

^^^^^^^^^^
resultchannel [discord.TextChannel]
^^^^^^^^^^

Set the channel application results go to. 
Leave blank to not send application results.
Output format: [member] was [accepted/denied] by [member] with the reason [reason]

Checks: ``Admin or Manage Server``

^^^^^^^^^^
acceptrole <discord.Role>
^^^^^^^^^^

The role that can accept or deny members.
This should be done carefully as roles can be assigned to others.
Discord hierachy rules apply.

Checks: ``Server Owner``

^^^^^^^^^^
custom
^^^^^^^^^^

Aliases: ``questions``

The bot will ask you in order all the way to 20:

``What will be question [number]``?

Response with the question you want when members apply. The limit is 20

Type ``done`` when finished. Reset to default by typing ``done`` at the first question.

Checks: ``Admin or Manage Server``

^^^^^^^^^^^^
settings
^^^^^^^^^^^^

View server settings for applications. This is available to all members.

Checks: ``None``

^^^^^^^^^^^^
positions
^^^^^^^^^^^^

View the IDs of the positions available.

Checks: ``None``

^^^^^^^^^^^^^
apply
^^^^^^^^^^^^^

Apply in the server. The bot will ask you either the default questions or the set questions.
The application will be sent to the configured channel in the server.
The command will not work if the application channel is not set

Checks: ``None``

^^^^^^^^^^^^
accept <discord.Member>
^^^^^^^^^^^^

Accept a members application. Won't work if they have not applied.
The role will be given from the list of available roles.
You can't accept a role higher than you.
Results will be sent to the resultchannel if there is one.

Checks: ``Custom: has acceptrole``

^^^^^^^^^^^^
accept <discord.Member>
^^^^^^^^^^^^

Deny a members application. Won't work if they have not applied.
Results will be sent to the resultchannel if there is one.

Checks: ``Custom: has acceptrole``  
==============
appset
==============

Settings for your servers applications

------------------
channel [discord.TextChannel]
------------------

Set the channel applications go to. 
Leave blank to clear and stop applications.

------------------
resultchannel [discord.TextChannel]
------------------
Set the channel where application results go to.

[usermention] was accepted/denied by [approved/denyer] with the reason [reason]

------------------
acceptrole [discord.Role]
------------------

Server Owner can set this. The role that can accept and deny users.

Discord Hierachy checks still apply.

--------------
questions/custom
--------------

Set the questions or custom questions for your server.

The bot will ask you each question, and you answer it with the question you want. Max of 20 questions.

Type <i> done </i> whenever you are done

^^^^^^^^^^^
Embed Block
^^^^^^^^^^^

.. autoclass:: tags.blocks.EmbedBlock

^^^^^^^^^^^^^^
Redirect Block
^^^^^^^^^^^^^^

.. autoclass:: tags.blocks.RedirectBlock

^^^^^^^^^^^^
Delete Block
^^^^^^^^^^^^

.. autoclass:: tags.blocks.DeleteBlock

^^^^^^^^^^^^^^
React Block
^^^^^^^^^^^^^^

.. autoclass:: tags.blocks.ReactBlock

^^^^^^^^^^^^^^
ReactU Block
^^^^^^^^^^^^^^

.. autoclass:: tags.blocks.ReactUBlock

--------------
Utility Blocks
--------------

The following utility blocks extend the power of tags that interface 
with bot commands.

.. _CommandBlock:

^^^^^^^^^^^^^
Command Block
^^^^^^^^^^^^^

.. autoclass:: tags.blocks.CommandBlock

^^^^^^^^^^^^^^
Override Block
^^^^^^^^^^^^^^

.. autoclass:: tags.blocks.OverrideBlock

Novaplanet scrapper
###################

Tous les soirs, radio nova nous concocte un petit mix sympa. Le probleme c'est
que la nuit, je dors.

Du coup voila comment ecouter la prog de nuit, mais pendant la journee !

Dans un crontab::

	0 0 * * * avconv -i http://novazz.ice.infomaniak.ch/novazz-128.mp3 -t 08:00:00 -acodec libvorbis /home/www/notmyidea.org/nova/nova-lanuit-`date +\%Y-\%m-\%d`.ogg && echo `date` > /tmp/stopped
	0 6 * * * /usr/bin/python /home/alexis/novaplanet/scrap.py /home/www/nova.notmyidea.org/

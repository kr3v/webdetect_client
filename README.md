# Webdetect checksum solution: different Python parts
## [client](client) 
Contains scripts that represent client of part of Webdetect checksum solution.
Latest implementation is [here](client/webdetect.py).

[This](client/webdetect_client.py) is example how [client](client/webdetect.py) can be used.
If we run it in following way:
```sh
python3 ./client/webdetect_client.py ./client/sample <path to leveldb generated by webdetect_java>
```
Then result is:
```
wordpress-cores 4.6.12 at /home/user/public_html
	wp.pformidable 2.02.09 at /home/user/public_html/wp-content/plugins/formidable
	wp.pbetter-wp-security 5.6.4 at /home/user/public_html/wp-content/plugins/better-wp-security
	wp.pcontact-form-7 4.5.1 at /home/user/public_html/wp-content/plugins/contact-form-7
	wp.pw3-total-cache 0.9.5.1 at /home/user/public_html/wp-content/plugins/w3-total-cache
	wp.pakismet 3.2 at /home/user/public_html/wp-content/plugins/akismet
	wp.td-lite 1.2 at /home/user/public_html/wp-content/themes/d-lite
	wp.tmeris 1.1.1 at /home/user/public_html/wp-content/themes/meris
```

## [scanner](scanner)
Dumps repository with app-versions (i.e. WordPress, Joomla, WP plugins directories) to CSV with checksums.
Latest implementation is [here](scanner/scanner.py).

Also note that file path might be also added to CSV by default (see `walk` method), which is not always required.

### Example
Generates `whitelist.csv`, which has to be processed by webdetect_java repository.

```sh
python3 scanner.py /storage/repo > whitelist.csv
```

## [server](server)
Deprecated, webdetect_java repo transforms CSV generated by scanner to leveldb DB.
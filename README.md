# Webdetect checksum solution: different Python parts
## [client](client) 
Contains scripts that represent client of part of Webdetect checksum solution.
Latest implementation is [here](client/webdetect_v2.py).

## [scanner](scanner)
Dumps repository with app-versions (i.e. WordPress, Joomla, WP plugins directories) to CSV with checksums.
Latest implementation is [here](scanner/scanner.py).

## [server](server)
Deprecated, webdetect_java repo transforms CSV generated by scanner to leveldb DB.
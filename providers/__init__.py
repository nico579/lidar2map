# providers/ — modules d'accès aux sources LiDAR nationales.
#
# Chaque module expose un sous-ensemble standard de constantes et fonctions
# (cf. fr_ign.py comme référence). lidar2map.py importe le provider via :
#   from providers import fr_ign as PROVIDER
#
# Pour ajouter un pays : copier fr_ign.py → <pays>_<source>.py et adapter
# URLs, CRS, format de nommage, layer WMS, etc.

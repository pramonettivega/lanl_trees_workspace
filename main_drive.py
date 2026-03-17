import os
import geopandas as gpd
import aux_funcs as af
import matplotlib.pyplot as plt
import numpy as np

#==============
#main user driver for running the maps!
#==============
#specify your project folder
pf = ''
#output folder
of = ''
#specify the case to run
name = ''
#specify a project crs (must be a projection in meters)
epsg = '5070'

#'''
#==============
#step 1: reproject the surface maps into your chosen crs...
#==============
files = ['rhof1', 'rhof10', 'rhof100', 
         'moist1', 'moist10', 'moist100',
         'depth', 'SAV']
for f in files:
    src_path = os.path.join(pf,name+'_'+f+'.tif')
    out_path = os.path.join(pf,name+'_'+f+'_'+str(epsg)+'.tif')
    dx, dy, nx, ny = af.reprojectRaster(src_path, epsg, out_path) #gives resolution in meters and pixels to be used in LANL trees later
nx = int(nx) 
ny = int(ny) 


#==============
#step 2: reproject the buildings into your chosen crs...
#==============
gdf = gpd.read_file(os.path.join(pf,name+'_generated_buildings_fireprops.geojson'))
gdf = gdf.set_crs(4326)
gdf = gdf.to_crs(epsg)

#==============
#step 3: reproject the trees into your chosen crs...
#==============
ht, ndatax, ndatay = af.writeTreelist(pf, name, epsg, gdf)
ht = int(ht)

#==============
#step 4: write the LANL treelist input file
#==============
af.writeFuellist(pf, name+'_treelist.txt', nx, ny, ht, dx, ndatax, ndatay)
import os
import geopandas as gpd
import aux_funcs as af
import matplotlib.pyplot as plt
import numpy as np

#==============
#main user driver for running the maps!
#==============
#specify the case to run
name = 'Forest'
#name = 'Prairie'
#specify your project folder
pf = '/Users/joliveto/Desktop/Projects/Rod_FuelMaps/2026-01_WUI_DataSend_UKO/'+name
#output folder
of = '/Users/joliveto/Desktop/Projects/Rod_FuelMaps/2026-01_WUI_DataSend_UKO/'+name
#specify a project crs (must be a projection in meters)
epsg = '5070'


#==============
#step 1: reproject the surface maps into your chosen crs...
#==============
files = [
         'rhof1', 'rhof10', 'rhof100', 
         'moist1', 'moist10', 'moist100',
         'depth', 'SAV'
        ]
for f in files:
    src_path = os.path.join(pf,name+'_'+f+'.tif')
    out_path = os.path.join(pf,name+'_'+f+'_'+str(epsg)+'.tif')
    dx, dy, nx, ny, bounds = af.reprojectRaster(src_path, epsg, out_path) #gives resolution in meters and pixels to be used in LANL trees later
nx = int(nx) 
ny = int(ny) 

xx, yy = af.reproject_to_match(os.path.join(pf,name+'_elevation.tif'), 
                               out_path, 
                               os.path.join(pf,name+'_elevation_'+str(epsg)+'.tif'))
print(xx,yy)


#==============
#step 2: Clip buildings & roads from unprojected treelist into your chosen crs...
#==============
gdf_trees = gpd.read_file(os.path.join(pf,name+'_Treelist.geojson'), crs="EPSG:4326")
gdf_build = gpd.read_file(os.path.join(pf,name+'_generated_buildings_fireprops.geojson'), crs="EPSG:4326")
gdf_roads = gpd.read_file(os.path.join(pf,name+'_roads.shp'), crs="EPSG:4326")
af.filterTreelist(gdf_trees,
                  gdf_build, 
                  gdf_roads,
                  epsg, 
                  pf, 
                  name)

#==============
#step 3: Write the treelist in txt format into your chosen crs...
#==============
ht, ndatax, ndatay = af.writeTreelist(pf, name, epsg, bounds)
ht = int(ht)
#'''
#==============
#step 4: write the LANL treelist input file
#==============
af.writeFuellist(pf, name+'_treelist_'+str(epsg)+'.txt', nx, ny, ht, dx, ndatax, ndatay)

#'''
#==============
#step 5: run LANL trees; Pedro this part will definitely require some fancy footwork
#==============
exe_name = 'trees.exe'
exe_path = '/Users/joliveto/Desktop/Projects/Rod_FuelMaps/2026-01_WUI_DataSend_UKO/scripts'
os.chdir(exe_path)
cmd_str = './%s %s' % (exe_name,  pf)
os.system(cmd_str)

'''

#==============
#step 6: replace surface fuels from LANL trees with the fuels we provided
#==============
    #rhof/density....
rhof_c = af.GetArrayData(os.path.join(pf,'treesrhof.dat'), 1, nx, ny, ht) #from the trees files...
rhof_s = af.GetTifData(os.path.join(pf,name+'_rhof1_'+str(epsg)+'.tif')).T
print(rhof_c.shape)
print(rhof_s.shape)
rhof_c[:,:,0] = rhof_s
af.writefiles(rhof_c,os.path.join(pf,'treesrhof.dat'))


    #moisture....
moist_c = af.GetArrayData(os.path.join(pf,'treesmoist.dat'), 1, nx, ny, ht) #from the trees files...
moist_s = af.GetTifData(os.path.join(pf,name+'_moist1_'+str(epsg)+'.tif'))
moist_c[:,:,0] = moist_s
af.writefiles(moist_c,os.path.join(pf,'treesmoist.dat'))
    #depth....
depth_c = af.GetArrayData(os.path.join(pf,'treesfueldepth.dat'), 1, nx, ny, ht) #from the trees files...
depth_s = af.GetTifData(os.path.join(pf,name+'_depth_'+str(epsg)+'.tif'))
depth_c[:,:,0] = depth_s
af.writefiles(depth_c,os.path.join(pf,'treesfueldepth.dat'))
    #sizescale....
size_c = af.GetArrayData(os.path.join(pf,'treesss.dat'), 1, nx, ny, ht) #from the trees files...
size_s = af.GetTifData(os.path.join(pf,name+'_SAV_'+str(epsg)+'.tif'))
size_s = 2/size_s #transform SAV to sizescale
size_c[:,:,0] = size_s
af.writefiles(size_c,os.path.join(pf,'treesss.dat'))

#OPTIONAL!!!!!!!!!!!!!: Write topography in fortran style for QUIC-Fire
topo = af.GetTifData(os.path.join(pf,name+'_elevation_'+str(epsg)+'.tif'))
af.writeTopo(os.path.join(pf,name+'_elevation_'+str(epsg)+'.dat'), topo)


#==============
#step 7: visualize the final results
#==============
rhof = af.GetArrayData(os.path.join(pf,'treesrhof.dat'), 1, nx, ny, ht)
rhof = np.ma.masked_where((rhof == 9999) | (rhof == 0), rhof)
rhof_s = rhof[:,:,0]
rhof_c = np.sum(rhof[:,:,1:], axis=2)

fig,axs = plt.subplots()
img = axs.imshow(rhof_s, cmap='Greens', origin='lower')
plt.colorbar(img,ax=axs)
axs.imshow(rhof_c, alpha=0.5, cmap='Reds', origin='lower')
plt.show()
'''
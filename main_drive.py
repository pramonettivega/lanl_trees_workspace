import os
import geopandas as gpd
import aux_funcs as af

#==============
#main user driver for running the maps!
#==============
#specify your project folder
pf = 'Inputs/'
#output folder
of = 'Outputs'
#specify the case to run
name = 'Tahoe'
#specify a project crs (must be a projection in meters)
epsg = '5070'

#==============
#step 1: reproject the surface maps into your chosen crs...
#==============
files = ['rhof1', 'rhof10', 'rhof100', 
         'moist',
         'depth', 'SAV']
for f in files:
    src_path = os.path.join(pf,name+'_'+f+'.tif')
    out_path = os.path.join(pf,name+'_'+f+'_'+str(epsg)+'.tif')
    dx, dy, nx, ny = af.reprojectRaster(src_path, epsg, out_path) #gives resolution in meters and pixels to be used in LANL trees later

#==============
#step 2: reproject the trees into your chosen crs...
#==============
ht, ndatax, ndatay = af.writeTreelist(pf, name, epsg)

#==============
#step 3: reproject the buildings into your chosen crs...
#==============
gdf = gpd.read_file(os.path.join(pf,name+'_generated_buildings_fireprops.geojson'))
gdf = gdf.set_crs(4326)
gdf = gdf.to_crs(epsg)

#==============
#step 4: write the LANL treelist input file
#==============
af.writeFuellist(pf, name+'_treelist.txt', nx, ny, ht, dx, ndatax, ndatay)

#==============
#step 5: run LANL trees; Pedro this part will definitely require some fancy footwork
#==============
exe_path = './Inputs/trees.exe'   # or wherever trees.exe actually is

cwd = os.getcwd()
os.chdir(pf)   # pf should be the folder containing fuellist
ret = os.system(exe_path)
os.chdir(cwd)

if ret != 0:
    raise RuntimeError("trees.exe failed")

#==============
#step 6: replace surface fuels from LANL trees with the fuels we provided
#==============
    #rhof/density....
rhof_c = af.GetArrayData(os.path.join(pf,'treesrhof.dat'), 1, nx, ny, ht) #from the trees files...
rhof_s = af.GetTifData(os.path.join(pf,name+'_rhof1_'+str(epsg)+'.tif'))
rhof_c[:,:,0] = rhof_s
af.writefiles(rhof_c,os.path.join(pf,'treesrhof.dat'))
    #moisture....
moist_c = af.GetArrayData(os.path.join(pf,'treesmoist.dat'), 1, nx, ny, ht) #from the trees files...
moist_s = af.GetTifData(os.path.join(pf,name+'_moist_'+str(epsg)+'.tif'))
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


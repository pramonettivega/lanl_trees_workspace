import numpy as np
import geopandas as gpd
import pandas as pd
import os
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import Affine
import math
from pathlib import Path
import numpy as np
import json
from shapely.geometry import box, mapping
from scipy.io import FortranFile
import sys
import matplotlib.pyplot as plt


def reproject_to_match(src_path, ref_path, out_path,
                       resampling=Resampling.nearest):
    with rasterio.open(ref_path) as ref:
        dst_crs       = ref.crs
        dst_transform = ref.transform
        dst_width     = ref.width      # = nx
        dst_height    = ref.height     # = ny
        dst_meta      = ref.meta.copy()

    with rasterio.open(src_path) as src:
        dst_meta.update({
            "crs"       : dst_crs,
            "transform" : dst_transform,
            "width"     : dst_width,
            "height"    : dst_height
        })

        # Create the destination file and reproject band‑by‑band
        with rasterio.open(out_path, "w", **dst_meta) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=resampling,
                )
    return int(dst_width), int(dst_height)

def reprojectRaster(src_path, target_epsg, out_path):
    # Open source raster
    with rasterio.open(src_path) as src:
        print(f"Source CRS: {src.crs}")
        # ---------------------------------------------------------
        # 2️⃣  Target CRS (make sure it is a proper string)
        # ---------------------------------------------------------
        dst_crs = f"EPSG:{int(target_epsg)}"
        print(f"Chosen target CRS: {dst_crs}")

        # ---------------------------------------------------------
        # 3️⃣  Compute the *correct* north‑up transform, width & height
        # ---------------------------------------------------------
        # This already gives a transform with b = d = 0 and e negative.
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        print(f"Target width/height: {width} x {height}")

        # ---------------------------------------------------------
        # 4️⃣  Extract pixel size (always positive numbers)
        # ---------------------------------------------------------
        x_res = transform.a               # pixel width  (metres)
        y_res = -transform.e              # pixel height (positive metres)

        if x_res == 0 or y_res == 0:
            raise ValueError("Zero pixel size detected – aborting.")

        # ---------------------------------------------------------
        # 5️⃣  Compute the bounds in the target CRS (xmin, ymin, xmax, ymax)
        # ---------------------------------------------------------
        left   = transform.c
        top    = transform.f
        right  = left + width * x_res
        bottom = top  - height * y_res
        bounds_target = (left, bottom, right, top)
        print(f"Target bounds (xmin, ymin, xmax, ymax): {bounds_target}")

        # ---------------------------------------------------------
        # 6️⃣  Prepare destination metadata – **use the original transform**
        # ---------------------------------------------------------
        dst_meta = src.meta.copy()
        dst_meta.update({
            "crs": dst_crs,
            "transform": transform,          # <-- keep the transform returned above
            "width": width,
            "height": height,
            # Preserve NoData if the source raster has one
            "nodata": src.nodata,
        })

        # ---------------------------------------------------------
        # 7️⃣  Write the re‑projected raster band‑by‑band
        # ---------------------------------------------------------
        with rasterio.open(out_path, "w", **dst_meta) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,   # <-- same transform we used for metadata
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest,
                )            
    
        return x_res, y_res, width, height, (transform.c, transform.f - height * y_res, transform.c + width * x_res, transform.f)
    

def writeTreelist(pf, name, epsg, bounds):
    #read treelist grojson
    df = gpd.read_file(os.path.join(pf,name+'_Treelist_'+epsg+'.geojson')) #read the tree list geojson

    #save the treelist
    fname = os.path.join(pf,name+'_treelist_'+str(epsg)+'.txt') #open a new file to write the treelist in .txt format for LANL trees
    print(fname)
    if os.path.exists(fname):
        os.remove(fname)
    file = open(fname, 'w')


    df['xcoor'] = df['X'] - bounds[0] #change the coordinates from projected to absolute coordinates
    df['ycoor'] = df['Y'] - bounds[1] #change the coordinates from projected to absolute coordinates
    print('extents x!',df['xcoor'].min(), df['xcoor'].max())
    print('extents y!',df['ycoor'].min(), df['ycoor'].max())

    for j in range(len(df)):
        sp    = 1#spcd_dict[str(df['SPCD'].iloc[j])][0] #species number
        xcoor = np.round(df['xcoor'].iloc[j], 3) #location coordinates
        ycoor = np.round(df['ycoor'].iloc[j], 3) #location coordinates
        ht    = np.round(df['HT'].iloc[j],2) #height [m]
        htlc  = np.round(df['CBH'].iloc[j],2) #height to live crown [m]
        cd    = np.round(df['DIA'].iloc[j],2) #max canopy diameter [m]
        htmcd = np.round(df['HT_TO_DIA'].iloc[j],2) #height to max canopy diameter [m]
        cbd   = np.round(df['CBD'].iloc[j],2) #0.087 #canopy bulk density [kg/m^3]
        fm    = 1.0 #fuel moisture content [%]
        ss    = 0.0005 #size scale
        #write new trees file
        file.write(str(sp)+'\t'+str(xcoor)+'\t'+str(ycoor)+'\t'+str(ht)
                +'\t'+str(htlc)+'\t'+str(cd)+'\t'+str(htmcd)+'\t'+str(cbd)
                +'\t'+str(fm)+'\t'+str(ss)+'\n')
    file.close
    ht = int(df['HT'].max())+1 #this will end up being your Nz in the 3D sim, so we want to make sure it's tall enough
    ndatax = df['xcoor'].max()
    ndatay = df['ycoor'].max()
    return ht, ndatax, ndatay

def writeFuellist(pf, treefile, nx, ny, nz, dx, ndatax, ndatay, dz='1.0', aa1='1.0'):
    #just make sure they're strings....
    ndatax = str(nx*dx)#str(int(ndatax)) 
    ndatay = str(ny*dx)#str(int(ndatay))
    nx = str(int(nx)) 
    ny = str(int(ny)) 
    nz = str(int(nz)) 
    dx = str(dx) 
    dz = str(dz)
    aa1 = str(aa1)
    #this will inherently run lanl trees with NO surface fuels
    if os.path.exists(os.path.join(pf,'fuellist')):
        os.remove(os.path.join(pf,'fuellist'))
    fp = open(os.path.join(pf,'fuellist'),'w')
    fp.write('&fuellist\n')
    fp.write('! FIRETEC domain info \n')
    fp.write('! ----------------------------------\n')
    fp.write('    nx  = '+nx+' \n')
    fp.write('    ny  = '+ny+' \n')
    fp.write('    nz  = '+nz+'    ! Size of HIGRAD/FIRETEC grid [cells]\n')
    fp.write('    dx  = '+dx+' \n')
    fp.write('    dy  = '+dx+' \n')
    fp.write('    dz  = '+dz+'        ! Grid Resolution [m]\n')
    fp.write('    aa1 = '+aa1+'       ! Vertical stretching component [default=0.1]\n')
    fp.write('    singlefuel = 1      ! Flag forcing single fuel type instead of multiple fuels\n')
    fp.write('    lreduced = 0        ! Flage to reduce output vertical number of cells to only layers with fuel\n')
    fp.write('    topofile = \'flat\'  	     \n')
    fp.write('! ----------------------------------\n')
    fp.write('! Input trees dataset info\n')
    fp.write('! ----------------------------------\n')
    fp.write('    itrees = 2                        ! Trees flag (1 is generalized tree data, 2 is specific tree data with locations, 3 is specific tree data with randomized locations)\n')
    fp.write('    treefile = \''+treefile+'\'\n')
    fp.write('    ndatax = '+ndatax+'   ! size of dataset domain in x direction [m]\n')
    fp.write('    ndatay = '+ndatay+'   ! size of dataset domain in y direction [m]\n')
    fp.write('    datalocx = 0          !x coordinate for bottom left corner where dataset should be placed \n')
    fp.write('    datalocy = 0          !y coordinate for bottom left corner where dataset should be placed \n')
    fp.write('! ----------------------------------\n')
    fp.write('! Litter switch\n')
    fp.write('! ----------------------------------\n')
    fp.write('    ilitter = 0                       ! Litter flag; 0=no litter, 1=basic litter, 2=DUET\n')
    fp.write('    !ilitter eq 1 (BASIC) info\n')
    fp.write('    litterconstant = 5  ! Exponential constant to determine increase of litter mass under trees\n')
    fp.write('    lrho = 4.67       ! litter bulk densities for each fuel type [kg/m3]\n')
    fp.write('    lmoisture = 0.07    ! litter moisture content [fraction]\n')
    fp.write('    lss = 0.0005      ! size scale of litter [m]\n')
    fp.write('    \n')
    fp.write('! ----------------------------------\n')
    fp.write('! Grass switch\n')
    fp.write('! ----------------------------------\n')
    fp.write('    igrass = 0                ! Grass flag; 1=generalized grass data\n')
    fp.write('    !igrass options \n')
    fp.write('    ngrass = 1                ! Number of Grass Species\n')
    fp.write('    grassconstant = 5         ! Exponential constant used to determine the decay of grass mass with tree shading\n')
    fp.write('    !GR1\n')
    fp.write('    grho = 1.0             ! grass bulk densities [kg/m3]\n')
    fp.write('    gmoisture = 0.15          ! grass moisture content [fraction]\n')
    fp.write('    gss = 0.0005            ! size scale of grass [m]\n')
    fp.write('    gdepth = 0.3            ! depth of grass [m]\n')
    fp.close()


def readfield(fuelfile, Nx, Ny, Nz):
    np.frombuffer(fuelfile.read(4),'f')
    return np.frombuffer(fuelfile.read(Nx*Ny*Nz*4), 'f').reshape((Nx,Ny,Nz),order='F')


def readfiles(datfile,Nx,Ny,Nz):
    fuel= np.zeros(Nx*Ny*Nz).reshape(Nx,Ny,Nz)
    fuelfile = open(datfile,'rb')
    fuel[:,:,:] = readfield(fuelfile,Nx,Ny,Nz)
    fuelfile.close()
    return fuel


def writefiles(fuel,fuelfile):
    if os.path.isfile(fuelfile):
        os.remove(fuelfile)
    f = FortranFile(fuelfile, 'w') #open fortran file
    #f.write_record(rhof.T )
    trhof = fuel.astype('float32')
    f.write_record(trhof.T)
    f.close()
    return 0

def writeTopo(fname,z):
    #z = np.transpose(z)
    z = z.astype('float32')
    if os.path.isfile(fname):
        os.remove(fname)
    file = FortranFile(fname, 'w')
    file.write_record(z)
    file.close()
    return 0

def GetArrayData(datfile, nfuel, Nx, Ny, Nz):
    #rhof is a 4D array: 1st position is species ID, 2nd is x, 3rd is y, 4th is z
    rhof = np.zeros(nfuel*Nx*Ny*Nz).reshape(nfuel,Nx,Ny,Nz)
    rhoffile = open(datfile,'rb')
    for ift in range(nfuel):
        rhof[ift,:,:,:] = readfield(rhoffile,Nx,Ny,Nz)
    rhoffile.close()
    arr = rhof[0,:,:,:]
    #arr = np.moveaxis(arr,0,1)
    return arr

def GetTifData(src_path):
    with rasterio.open(src_path) as src:
        # -------------------------------------------------------------
        # 1️⃣  Read the raw band
        # -------------------------------------------------------------
        data = src.read(1)                     # shape = (rows, cols)

        # -------------------------------------------------------------
        # 2️⃣  If the raster is already north‑up, just return it
        # -------------------------------------------------------------
        if src.transform.b == 0 and src.transform.d == 0:
            return data

        # -------------------------------------------------------------
        # 3️⃣  Extract the six affine coefficients safely
        # -------------------------------------------------------------
        # Option 1 – using the built‑in helper (works on all recent rasterio):
        a, b, c, d, e, f = src.transform.to_gdal()
        # (You could also do:
        # a, b, c, d, e, f = (src.transform.a, src.transform.b,
        #                     src.transform.c, src.transform.d,
        #                     src.transform.e, src.transform.f)
        # )  

        pixel_width  = a                # metres per column (east‑west)
        pixel_height = -e               # positive metres per row (north‑south)

        # -------------------------------------------------------------
        # 4️⃣  Compute the bounds of the original raster
        # -------------------------------------------------------------
        left, bottom, right, top = src.bounds

        # -------------------------------------------------------------
        # 5️⃣  Build a new north‑up affine (no rotation/shear)
        # -------------------------------------------------------------
        new_transform = Affine(pixel_width, 0, left,
                               0, -pixel_height, top)

        # Destination array – keep original dimensions
        dst = np.empty((src.height, src.width), dtype=data.dtype)

        # -------------------------------------------------------------
        # 6️⃣  Reproject onto the north‑up grid
        # -------------------------------------------------------------
        reproject(
            source=data,
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=new_transform,
            dst_crs=src.crs,                 # only orientation changes
            resampling=Resampling.nearest,   # change if you need smoother resampling
        )

        # -------------------------------------------------------------
        # 7️⃣  Return the north‑up array
        # -------------------------------------------------------------
        return dst

def filterTreelist(trees:gpd.GeoDataFrame, 
                   buildings:gpd.GeoDataFrame, 
                   roads:gpd.GeoDataFrame, 
                   epsg:str, 
                   out_path:str, 
                   name:str):
    # Exclusion Parameters
    ROAD_BUFFER = 5.0           # Road buffer in meters
    BUILDING_BUFFER = 5.0        # Building buffer in meters
    out_file = os.path.join(out_path,name+'_Treelist.geojson')
    # -------------------
    print(f"Cleaning existing treelist")
    print(f"Exclusion Parameters: Road Buffer={ROAD_BUFFER}m, Building Buffer={BUILDING_BUFFER}m")
    
    print(f"Reprojecting to {epsg}...")
    trees = trees.to_crs(int(epsg))
    trees['X'] = trees.geometry.x.round(2)
    trees['Y'] = trees.geometry.y.round(2)
    buildings = buildings.to_crs(epsg)
    roads = roads.to_crs(epsg)

    # 2. Create Exclusion Mask
    print("Creating exclusion corridors...")
    
    # Buffer roads
    roads_mask = roads.buffer(ROAD_BUFFER).to_frame(name='geometry')
    # Buffer buildings
    buildings_mask = buildings.buffer(BUILDING_BUFFER).to_frame(name='geometry')
    
    # Combine masks for spatial join
    # We use a combined GeoDataFrame of all exclusion areas
    exclusion_gdf = pd.concat([roads_mask, buildings_mask], ignore_index=True)
    # Dissolve to speed up join
    exclusion_mask_single = exclusion_gdf.union_all()
    exclusion_mask_gdf = gpd.GeoDataFrame({'geometry': [exclusion_mask_single]}, crs=epsg)

    # 3. Filter Trees
    print("Identifying trees in restricted zones (buildings/roads)...")
    # Spatial join: find trees that intersect the exclusion mask
    joined = gpd.sjoin(trees, exclusion_mask_gdf, how='left', predicate='intersects')
    
    # Keep only trees that did NOT intersect (index_right will be NaN)
    trees_clean = joined[joined['index_right'].isna()].copy()
    
    # Clean up sjoin columns
    if 'index_right' in trees_clean.columns:
        trees_clean = trees_clean.drop(columns=['index_right'])

    # 4. Finalize and Save
    print(f"Original trees: {len(trees)}")
    print(f"Trees removed:  {len(trees) - len(trees_clean)}")
    print(f"Trees remaining: {len(trees_clean)}")
    print(f"Saving ...")
    trees_clean.to_file(os.path.join(out_path,name+'_Treelist_'+str(epsg)+'.geojson'), driver='GeoJSON')

    # Reproject back to original CRS (EPSG:4326)
    print("Reprojecting to EPSG:4326...")
    trees_clean = trees_clean.to_crs('EPSG:4326')
    
    # Update X/Y columns to match geometry (6 decimal precision)
    if 'X' in trees_clean.columns and 'Y' in trees_clean.columns:
        trees_clean['X'] = trees_clean.geometry.x.round(6)
        trees_clean['Y'] = trees_clean.geometry.y.round(6)
        trees_clean['geometry'] = gpd.points_from_xy(trees_clean['X'], trees_clean['Y'])

    print(f"Saving ...")
    trees_clean.to_file(out_file, driver='GeoJSON')
    print("Done.")











import numpy as np
import geopandas as gpd
import pandas as pd
import os
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import math
from pathlib import Path
import numpy as np
import json
from shapely.geometry import box, mapping
from scipy.io import FortranFile


def reprojectRaster(src_path, target_epsg, out_path):
    # Open source raster (expects EPSG:4326)
    with rasterio.open(src_path) as src:
        print(f"Source CRS: {src.crs}")

        # Target CRS
        target_crs = f"EPSG:{target_epsg}"
        print(f"Chosen target CRS: {target_crs}")

        # Compute transform, dimensions for target CRS
        transform, width, height = calculate_default_transform(
            src.crs, target_crs, src.width, src.height, *src.bounds
        )
        print(f"Target width/height: {width} x {height}")

        # Prepare metadata for output file
        kwargs = src.meta.copy()
        kwargs.update({
            "crs": target_crs,
            "transform": transform,
            "width": width,
            "height": height
        })

        # Reproject each band and write to out_path
        with rasterio.open(out_path, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.nearest
                )

        # Optional: return pixel size and total size in metres
        x_res = transform[0]      # pixel width (metres)
        y_res = -transform[4]     # pixel height (metres, positive)
        width_m = width * x_res
        height_m = height * y_res
        return x_res, y_res, width_m, height_m

def writeTreelist(pf, name, epsg):
    #read treelist grojson
    df = gpd.read_file(os.path.join(pf,name+'_Treelist.geojson')) #read the tree list geojson
    df = df.set_crs(4326) #set epsg to unprojected lat/lon)
    df = df.to_crs(epsg) #change epsg to projected lat/lon THIS HAS TO BE IN METERS!!!

    #save the treelist
    fname = os.path.join(pf,name) #open a new file to write the treelist in .txt format for LANL trees
    if os.path.exists(fname):
        os.remove(fname)
    file = open(fname, 'w')

    df['xcoor'] = df['X'] - df['X'].min() #change the coordinates from projected to absolute coordinates
    df['ycoor'] = df['Y'] - df['Y'].min() #change the coordinates from projected to absolute coordinates

    for j in range(len(df)):
        sp    = 1#spcd_dict[str(df['SPCD'].iloc[j])][0] #species number
        xcoor = int(df['xcoor'].iloc[j]) #location coordinates
        ycoor = int(df['ycoor'].iloc[j]) #location coordinates
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
    nx = str(int(nx)) 
    ny = str(int(ny)) 
    nz = str(int(nz)) 
    dx = str(dx) 
    ndatax = str(int(ndatax)) 
    ndatay = str(int(ndatay))
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
        data = src.read(1)
    return data




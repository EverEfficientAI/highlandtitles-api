from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2 import sql
from pyproj import Transformer
import logging
import os
from bng_latlon import OSGB36toWGS84

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logging.info("Application startup complete.")

# Database connection parameters
db_params = {
    'dbname': os.getenv('DATABASE_NAME'),
    'user': os.getenv('DATABASE_USER'),
    'password': os.getenv('DATABASE_PASSWORD'),
    'host': os.getenv('DATABASE_HOST'),
    'port': os.getenv('DATABASE_PORT')
}
# Log the database connection parameters
logging.info(f"Database connection parameters: {db_params}")

def get_db_connection():
    conn = psycopg2.connect(
        dbname=db_params['dbname'],
        user=db_params['user'],
        password=db_params['password'],
        host=db_params['host'],
        port=db_params['port']
    )
    return conn

class Plot(BaseModel):
    PlotNumber: str
    OSx: float
    OSy: float
    Latitude: float
    Longitude: float
    GoogleMapsLink: str

@app.get("/plot/{plot_number}", response_model=Plot)
async def read_plot(plot_number: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = sql.SQL("SELECT OSx, OSy FROM plots WHERE PlotNumber = %s")
    cursor.execute(query, (plot_number,))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if result:
        osx, osy = result

        # Convert to integers and scale down by removing the last three digits
        try:
            osx = float(str(int(osx))[:-3])
            osy = float(str(int(osy))[:-3])
        except ValueError:
            raise HTTPException(status_code=500, detail="Invalid OSx or OSy values in database.")

        # Log the coordinates before transformation
        logging.info(f"Trimmed coordinates: OSx={osx}, OSy={osy}")

        try:
            # Convert OSGB36 to WGS84
            # transformer = Transformer.from_crs("EPSG:27700", "EPSG:4326")
            # lat, lon = transformer.transform(osx, osy)  
            lat, lon = OSGB36toWGS84(osx, osy)
            
            # Log the transformation results
            logging.info(f"Transformed coordinates: lat={lat}, lon={lon}")

            # Check for valid float values
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise HTTPException(status_code=500, detail="Invalid latitude or longitude values.")
            # "https://www.google.com/maps/@{lat},{lon},{zoom}
            google_maps_link = f"https://www.google.com/maps/@{lat},{lon},15z"
            return {"PlotNumber": plot_number, "OSx": osx, "OSy": osy, "Latitude": lat, "Longitude": lon, "GoogleMapsLink": google_maps_link}
        
        except Exception as e:
            logging.error(f"Error in coordinate transformation: {e}")
            raise HTTPException(status_code=500, detail="Error in coordinate transformation.")
    else:
        raise HTTPException(status_code=404, detail="PlotNumber not found")

@app.get("/")
def read_root():
    return {"Hello": "World"}
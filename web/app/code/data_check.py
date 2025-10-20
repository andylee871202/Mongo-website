import pandas as pd
import configparser
from Mongo_manager import MongoManager as MM

config = configparser.ConfigParser()
config.read('/app/config.env')
mongo_manager = MM()


data_df = pd.read_csv('/app/web/app/ori_data/poem.csv', sep='\t')


import pandas as pd
import configparser
from Mongo_manager import MongoManager as MM

data_df = pd.read_csv('/app/web/app/ori_data/poem.csv', sep='\t')


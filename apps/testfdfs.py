from fdfs_client.client import Fdfs_client

client = Fdfs_client('client.ini')
ret = client.upload_by_filename('a.txt')
print(ret)


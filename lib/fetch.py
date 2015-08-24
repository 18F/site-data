import requests, json
class Fetch():
  def __init__(self, url):
    self.url = url.strip()

  def get_data_from_url(self):
    response = requests.get(self.url)
    return response.json()

  def save_data(self, data, filename):
    target = open(filename, 'w')
    if type(data) is dict or type(data) is list:
      target.write(json.dumps(data))
      target.close()
      return True
    else:
      return False

  def get_data_from_file(self, filename):
    target = open(filename)
    return json.load(target)

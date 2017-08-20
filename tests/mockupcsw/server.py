from flask import Flask
from flask import request, render_template
app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        return render_template("getidentifiers.xml")
    if request.method == 'GET':
        is_meta = {"version": ["2.0.2"], "request": ["GetCapabilities"], "service": ["CSW"]}
        if dict(request.args) == is_meta:
            return render_template("metadata.xml")
        is_resource = [
            {'outputFormat': [u'application/xml'], 'version': [u'2.0.2'], 'service': [u'CSW'], 'outputSchema': [u'http://www.isotc211.org/2005/gmd'], 'elementsetname': [u'full'], 'request': [u'GetRecordById'], 'id': [u'4e73fafe-3534-411e-98c7-765d385bd18d']},
            {'outputFormat': [u'application/xml'], 'version': [u'2.0.2'], 'service': [u'CSW'], 'outputSchema': [u'http://www.isotc211.org/2005/gmd'], 'elementsetname': [u'full'], 'request': [u'GetRecordById'], 'id': [u'5c708173-8129-4b9e-a546-1617e251974b']},
            {'outputFormat': [u'application/xml'], 'version': [u'2.0.2'], 'service': [u'CSW'], 'outputSchema': [u'http://www.isotc211.org/2005/gmd'], 'elementsetname': [u'full'], 'request': [u'GetRecordById'], 'id': [u'a9a13167-98ff-4405-bed7-6690db4620c4']}
        ]
        for num, resource in enumerate(is_resource):
            if dict(request.args) == resource:
                return render_template("resource_{}.xml".format(num))
    return 'Hello, World!'

#API 9 Main
"""
Upload Format

{
    "event_type": "$event_type$",
    "device_name": "$device_name$",
    "mac_address": "$mac_address$",
    "sn": "$sn$",
    "time": "$time$",
    "detection_region": "$detection_region$",
    "detection_region_name": "$detection_region_name$",
    "license_plate": "$license_plate$",
    "country_region": "$country_region$",
    "plate_type": "$plate_type$",
    "vehicle_type": "$vehicle_type$",
    "confidence": "#confidence#",
    "confidence_int": "#confidence_int#",
    "direction": "$direction$",
    "motion_direction": "$motion_direction$",
    "resolution_width": "$resolution_width$",
    "resolution_height": "$resolution_height$",
    "coordinate_x1": "$coordinate_x1$",
    "coordinate_y1": "$coordinate_y1$",
    "coordinate_x2": "$coordinate_x2$",
    "coordinate_y2": "$coordinate_y2$",
    "vehicle_tracking_box_x1": "$vehicle_tracking_box_x1$",
    "vehicle_tracking_box_y1": "$vehicle_tracking_box_y1$",
    "vehicle_tracking_box_x2": "$vehicle_tracking_box_x2$",
    "vehicle_tracking_box_y2": "$vehicle_tracking_box_y2$",
    "license_plate_snapshot": "$license_plate_snapshot$",
    "vehicle_snapshot": "$vehicle_snapshot$",
    "full_snapshot": "$full_snapshot$"
}
"""

import json
import os
import sys
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, date

request_max_size = 1000000
camera_whitelist_active = False
camera_whitelist = []


class Server(BaseHTTPRequestHandler):

    def send_fail(self, code, content, mime_type = "application/json"):
        if isinstance(content, dict):
            content = json.dumps(content)
        if isinstance(content, str):
            content = content.encode("utf-8")
        print(content)
        self.send_response(code)
        self.send_header("content-type", mime_type)
        self.send_header("content-length", len(content))
        self.end_headers()
        self.wfile.write(content)
        return
    
    def handle_anpr(self):
        #Check whitelist
        sn = self.body.get("sn")
        mac = self.body.get("mac_address")
        if camera_whitelist_active and not (sn in camera_whitelist or mac in camera_whitelist):
            data = {"success": "-1", "content": "This camera is not whitelisted to upload data to this api."}
            return self.send_fail(403, data)
        
        #Process and save data.
        self.date = str(date.today())
        self.daily_dir = f"files/{self.date}"
        self.plate = self.body.get("license_plate")
        self.plate_dir = f"{self.daily_dir}/{self.plate}"
        if not os.path.isdir(self.plate_dir):
            os.makedirs(self.plate_dir)
        dt = datetime.strptime(self.body.get("time"), "%Y-%m-%d %H:%M:%S.%f")
        timestamp = dt.timestamp()
        timestamp = str(timestamp).split(".")
        timestamp = [timestamp[0][-5:],timestamp[1][:2]]
        print(timestamp)
        timestamp = "".join(timestamp)
        self.name = f"{self.plate_dir}/{timestamp}"
        print(self.name)
        
        self.plate_snapshot = self.body.pop("license_plate_snapshot", None)
        self.vehicle_snapshot = self.body.pop("vehicle_snapshot", None)
        self.full_snapshot = self.body.pop("full_snapshot", None)
        
        self.body["timestamp"] = timestamp
        print(self.body)
        with open(f"{self.name}.json", "wb") as f:
            content = json.dumps(body).encode("utf-8")
            f.write(content)
        
        if self.plate_snapshot:
            with open(f"{self.name}_plate.jpg", "wb") as f:
                im = base64.b64decode(self.plate_snapshot)
                f.write(im)
        if self.vehicle_snapshot:
            with open(f"{self.name}_vehicle.jpg", "wb") as f:
                im = base64.b64decode(self.vehicle_snapshot)
                f.write(im)
        if self.full_snapshot:
            with open(f"{self.name}_full.jpg", "wb") as f:
                im = base64.b64decode(self.full_snapshot)
                f.write(im)
            
        
            
        
        return
    def do_GET(self):
        #Stop Weird Requests
        valid_paths = ["/", "/index", "/status", "/hello"]
        if self.path not in valid_paths:
            self.send_error(400, f"Invalid URI - try {json.dumps(valid_paths)}")
            return
        
        #Send Status Response
        content_json_dic = {
            "Time": datetime.now().ctime(),
            "Status": "API_1 Server OK",
        }
        content_bytes = json.dumps(content_json_dic).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", len(content_bytes))
        self.end_headers()
        self.wfile.write(content_bytes)
        return
    def do_POST(self):
        print("Handling POST")
        #Check Content type and size is appropriate.
        try:
            clength = int(self.headers["Content-Length"])
            ctype = self.headers["Content-Type"]
            print(f"File Size: {clength}\nFile Type: {ctype}")
        except (KeyError, TypeError) as e:
            self.send_error(400, f"Unable to parse 'Content-Length' or 'Content-Type' Header - Error: {e}")
            return
        if clength > request_max_size:
            data = {"success": "-1", "content": f"Request excceeds max size\nRequest Size: {clength}"}
            self.send_fail(400, data)
            return
        if ctype.find("application/json") < 0:
            data = {"success": "0", "content": "Not JSON error"}
            self.send_fail(400, data)
            return

        #Check Content is Correctly Formatted
        body = self.rfile.read(clength)
        self.body = json.loads(body.decode("utf-8"))
        event = self.body.get("event_type")
        if event == "Regular":
            return self.handle_anpr()

def run(server_class=HTTPServer, handler_class=Server, port=8000):
    server_address = ("127.0.0.1", port)
    server_address = ("" , port) #Allows access from outside nginx
    httpd = server_class(server_address, handler_class)
    try:
        print("Starting api9 on port %d..." % port)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Server...")
        sys.exit()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        run(port=int(sys.argv[1]))
    else:
        run()

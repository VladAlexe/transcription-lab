"""Captură QA prin Edge DevTools; nu este necesar la rularea aplicației."""
from __future__ import annotations
import base64,json,sys,time,urllib.request
from pathlib import Path
from websockets.sync.client import connect

PORT=9223; ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"screenshots"


def targets()->list[dict]:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json",timeout=5) as response:return json.load(response)


def command(socket,identifier:int,method:str,params:dict|None=None)->dict:
    socket.send(json.dumps({"id":identifier,"method":method,"params":params or {}}))
    while True:
        message=json.loads(socket.recv())
        if message.get("id")==identifier:return message


def main()->None:
    OUT.mkdir(exist_ok=True);target=next(x for x in targets() if x["type"]=="page")
    with connect(target["webSocketDebuggerUrl"],origin="http://localhost") as socket:
        identifier=1
        screens=() if "--dark-only" in sys.argv else ("welcome","file","transcription","speakers","export","missing")
        for screen in screens:
            for scale in (1.0,1.25,1.5):
                command(socket,identifier,"Emulation.setDeviceMetricsOverride",{"width":1240,"height":820,"deviceScaleFactor":scale,"mobile":False});identifier+=1
                command(socket,identifier,"Page.navigate",{"url":f"http://127.0.0.1:8550/?screen={screen}"});identifier+=1
                time.sleep(4)
                response=command(socket,identifier,"Page.captureScreenshot",{"format":"png","captureBeyondViewport":False});identifier+=1
                (OUT/f"{screen}-{int(scale*100)}.png").write_bytes(base64.b64decode(response["result"]["data"]))
        command(socket,identifier,"Emulation.setDeviceMetricsOverride",{"width":1240,"height":820,"deviceScaleFactor":1.0,"mobile":False});identifier+=1
        command(socket,identifier,"Page.navigate",{"url":"http://127.0.0.1:8550/?screen=file&dark=1"});identifier+=1
        time.sleep(4);response=command(socket,identifier,"Page.captureScreenshot",{"format":"png","captureBeyondViewport":False})
        (OUT/"dark-file-100.png").write_bytes(base64.b64decode(response["result"]["data"]))


if __name__=="__main__":main()

"""python3 -m clientmodel: list, show and resolve client models.

  python3 -m clientmodel list
  python3 -m clientmodel show NAME          the model with its bases merged (JSON)
  python3 -m clientmodel resolve NAME       the options it resolves to (JSON)
  python3 -m clientmodel wpa-conf NAME --ssid SSID [--psk PSK] [--key-mgmt K] [--ctrl-interface DIR]
  python3 -m clientmodel iwd-conf NAME      iwd's main.conf

NAME is a nickname with optional behaviours, for example pixel+btm-refuser.
"""

import argparse
import json
import sys
from pathlib import Path

from .resolve import MODELS, ModelError, iwd_conf, list_models, load, resolve, wpa_conf


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m clientmodel", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", type=Path, default=MODELS, help="the models directory")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    for name in ("show", "resolve", "iwd-conf"):
        sub.add_parser(name).add_argument("name")
    w = sub.add_parser("wpa-conf")
    w.add_argument("name")
    w.add_argument("--ssid", required=True)
    w.add_argument("--psk")
    w.add_argument("--key-mgmt", default="WPA-PSK")
    w.add_argument("--ctrl-interface", default="/var/run/wpa_supplicant")
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            print(json.dumps(list_models(args.models), indent=2))
        elif args.command == "show":
            print(json.dumps(load(args.name, args.models), indent=2, ensure_ascii=False))
        elif args.command == "resolve":
            print(json.dumps(resolve(args.name, args.models), indent=2))
        elif args.command == "wpa-conf":
            sys.stdout.write(wpa_conf(resolve(args.name, args.models), args.ssid, args.psk,
                                      args.key_mgmt, args.ctrl_interface))
        elif args.command == "iwd-conf":
            sys.stdout.write(iwd_conf(resolve(args.name, args.models)))
    except ModelError as e:
        print(f"clientmodel: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

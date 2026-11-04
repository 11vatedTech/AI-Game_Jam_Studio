from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from . import __version__
from .config import StudioConfig, write_default_config
from .errors import StudioError
from .service import StudioService
from .mcp import serve as serve_mcp

def _print(value): print(json.dumps(value,indent=2,sort_keys=True,default=str))
def _service(args): return StudioService(StudioConfig.load(Path(args.home).expanduser() if getattr(args,"home",None) else None))
def _require_human_confirmation(label: str, identifier: str) -> None:
    if not sys.stdin.isatty(): raise ValueError("This action requires an interactive human terminal; it cannot be approved by a non-interactive agent process")
    phrase=f"{label} {identifier[-6:]}"
    print(f"\nHuman confirmation required. Review the requested action and type exactly: {phrase}")
    if input("> ").strip()!=phrase: raise ValueError("Human confirmation phrase did not match")

def build_parser():
    p=argparse.ArgumentParser(prog="studio",description="11vatedTech AI Game Jam Studio runtime")
    p.add_argument("--home",help="Studio data directory (or set STUDIO_HOME)")
    p.add_argument("--version",action="version",version=__version__)
    sub=p.add_subparsers(dest="command",required=True)
    init=sub.add_parser("init",help="Initialize local state, configuration and workspace")
    init.add_argument("--force-noop",action="store_true",help=argparse.SUPPRESS)
    sub.add_parser("status",help="Show runtime status")
    sub.add_parser("doctor",help="Inspect current host and installed applications")
    caps=sub.add_parser("capabilities",help="List registered capabilities")
    caps.add_argument("--domain")
    job=sub.add_parser("job",help="Durable production jobs"); js=job.add_subparsers(dest="job_command",required=True)
    create=js.add_parser("create"); create.add_argument("spec",type=Path)
    run=js.add_parser("run"); run.add_argument("job_id"); run.add_argument("--approval-id")
    status=js.add_parser("status"); status.add_argument("job_id")
    reconcile=js.add_parser("reconcile",help="Human-only recovery of an uncertain in-flight task")
    reconcile.add_argument("job_id"); reconcile.add_argument("task_id")
    reconcile.add_argument("--action",choices=["retry","mark_succeeded"],required=True)
    reconcile.add_argument("--reviewer",required=True); reconcile.add_argument("--evidence",required=True)
    reconcile.add_argument("--outputs-json",type=Path,help="JSON object of task outputs; required for mark_succeeded")
    listing=js.add_parser("list"); listing.add_argument("--status"); listing.add_argument("--limit",type=int,default=100)
    art=sub.add_parser("artifacts"); ars=art.add_subparsers(dest="artifact_command",required=True)
    ars.add_parser("list").add_argument("--job-id")
    ver=ars.add_parser("verify"); ver.add_argument("artifact_id")
    ar=ars.add_parser("review"); ar.add_argument("artifact_id"); ar.add_argument("--reviewer",required=True)
    ar.add_argument("--license-status",choices=["cleared","restricted","unknown","blocked"])
    ar.add_argument("--license-identifier"); ar.add_argument("--license-source-url")
    ar.add_argument("--validation-status",choices=["NOT_RUN","PASS","FAIL"]); ar.add_argument("--notes",default="")
    quality=sub.add_parser("quality"); qs=quality.add_subparsers(dest="quality_command",required=True)
    qr=qs.add_parser("report"); qr.add_argument("job_id")
    rev=qs.add_parser("review"); rev.add_argument("job_id"); rev.add_argument("--type",dest="review_type",required=True,choices=["technical","creative","rights","performance","accessibility","release"])
    rev.add_argument("--verdict",required=True,choices=["PASS","FAIL"]); rev.add_argument("--reviewer",required=True); rev.add_argument("--rationale",required=True); rev.add_argument("--evidence",action="append",default=[])
    approval=sub.add_parser("approvals"); aps=approval.add_subparsers(dest="approval_command",required=True)
    aps.add_parser("list").add_argument("--status")
    req=aps.add_parser("request"); req.add_argument("--scope",required=True); req.add_argument("--side-effect",required=True); req.add_argument("--target",required=True); req.add_argument("--reason",required=True)
    dec=aps.add_parser("decide"); dec.add_argument("approval_id"); dec.add_argument("--approve",action="store_true"); dec.add_argument("--reject",action="store_true"); dec.add_argument("--approver",required=True)
    dbp=sub.add_parser("database",help="Database integrity and backup tools"); dbs=dbp.add_subparsers(dest="database_command",required=True)
    dbs.add_parser("integrity-check")
    backup=dbs.add_parser("backup"); backup.add_argument("--destination",type=Path)
    mcp=sub.add_parser("mcp"); ms=mcp.add_subparsers(dest="mcp_command",required=True); ms.add_parser("serve",help="Serve MCP over stdio")
    return p

def main(argv=None):
    args=build_parser().parse_args(argv)
    try:
        if args.command=="init":
            home=Path(args.home).expanduser().resolve() if args.home else Path(os.environ.get("STUDIO_HOME",Path.home()/".11vated-studio")).expanduser().resolve()
            write_default_config(home); service=StudioService(StudioConfig.load(home))
            _print({"status":"INITIALIZED","home":str(home),"workspace":str(service.config.workspace),"config":str(home/"config.toml"),"policy":str(service.config.policy_file)})
        elif args.command=="status": _print(_service(args).status())
        elif args.command=="doctor": _print(_service(args).doctor())
        elif args.command=="capabilities": _print(_service(args).registry.list(args.domain))
        elif args.command=="job":
            service=_service(args)
            if args.job_command=="create": _print(service.jobs.create(json.loads(args.spec.read_text(encoding="utf-8"))))
            elif args.job_command=="run": _print(service.jobs.run(args.job_id,args.approval_id))
            elif args.job_command=="status": _print(service.jobs.status(args.job_id))
            elif args.job_command=="reconcile":
                _require_human_confirmation("RECONCILE",args.job_id)
                outputs=None
                if args.outputs_json:
                    outputs=json.loads(args.outputs_json.read_text(encoding="utf-8"))
                    if not isinstance(outputs,dict): raise ValueError("--outputs-json must contain a JSON object")
                if args.action=="mark_succeeded" and outputs is None:
                    raise ValueError("--outputs-json is required for --action mark_succeeded")
                if args.action=="retry" and outputs is not None:
                    raise ValueError("--outputs-json is not permitted for --action retry")
                _print(service.jobs.reconcile(args.job_id,args.task_id,action=args.action,reviewer=args.reviewer,
                                               evidence=args.evidence,outputs=outputs))
            else: _print(service.jobs.list(args.status,args.limit))
        elif args.command=="artifacts":
            service=_service(args)
            if args.artifact_command=="list": _print(service.artifacts.list(args.job_id))
            elif args.artifact_command=="verify": _print(service.artifacts.verify(args.artifact_id))
            else:
                _require_human_confirmation("REVIEW",args.artifact_id)
                _print(service.artifacts.review(args.artifact_id,reviewer=args.reviewer,license_status=args.license_status,
                    license_identifier=args.license_identifier,license_source_url=args.license_source_url,
                    validation_status=args.validation_status,notes=args.notes))
        elif args.command=="quality":
            service=_service(args)
            if args.quality_command=="report": _print(service.quality_report(args.job_id))
            else:
                _require_human_confirmation("REVIEW",args.job_id)
                _print(service.record_quality_review(args.job_id,review_type=args.review_type,verdict=args.verdict,
                     reviewer=args.reviewer,rationale=args.rationale,evidence=args.evidence))
        elif args.command=="approvals":
            service=_service(args)
            if args.approval_command=="request": _print(service.policy.request(args.scope,args.side_effect,args.target,args.reason))
            elif args.approval_command=="list": _print(service.policy.list(args.status))
            else:
                if args.approve==args.reject: raise ValueError("Specify exactly one of --approve or --reject")
                if args.approve: _require_human_confirmation("APPROVE",args.approval_id)
                _print(service.policy.decide(args.approval_id,args.approve,args.approver))
        elif args.command=="database":
            service=_service(args)
            if args.database_command=="integrity-check": _print(service.db.integrity_check())
            else:
                import datetime
                target=args.destination or (service.config.home/"backups"/f"studio-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.sqlite3")
                _print(service.db.backup(target))
        elif args.command=="mcp": serve_mcp(_service(args))
        return 0
    except (StudioError,ValueError,OSError,KeyError,json.JSONDecodeError) as exc:
        print(json.dumps({"error":getattr(exc,"code","COMMAND_FAILED"),"message":str(exc),"details":getattr(exc,"details",{})},indent=2),file=sys.stderr)
        return 2

if __name__=="__main__": raise SystemExit(main())

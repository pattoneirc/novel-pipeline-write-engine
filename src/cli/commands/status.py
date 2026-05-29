"""Status and doctor commands."""
from __future__ import annotations

import sys
try:
    from novel_pipeline.version import get_version
except ImportError:
    from version import get_version
from .common import PROJECT_ROOT, SRC_GUARDS_DIR


def cmd_status(detail=False):
    """Run doctor.py for environment diagnostics. --detail for verbose output."""
    print("=" * 60)
    v = get_version()
    print(f"  Novel Pipeline - Write Engine {v}")
    mode_str = "详细" if detail else "标准"
    print(f"  状态检查 ({mode_str})")
    print("=" * 60)
    print()

    try:
        from doctor import main as doctor_main
        return doctor_main(detail=detail)
    except ImportError:
        # Fallback manual check
        print("  Running manual status check...")
        all_ok = True
        import platform as _platform

        # OS
        _os = _platform.system()
        ok = True
        print(f"  [OK] OS: {_os} {_platform.release()}")

        # Python version
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        ok = sys.version_info >= (3, 10)
        mark = "OK" if ok else "FAIL"
        print(f"  [{mark}] Python {py_ver}")
        all_ok &= ok

        # config.json
        cfg = PROJECT_ROOT / "config.json"
        ok = cfg.exists()
        mark = "OK" if ok else "MISSING"
        print(f"  [{mark}] config.json")
        all_ok &= ok

        # src/guards/
        ok = (SRC_GUARDS_DIR / "reader_pull_guard.py").exists()
        mark = "OK" if ok else "MISSING"
        print(f"  [{mark}] src/guards/reader_pull_guard.py")
        all_ok &= ok

        ok = (SRC_GUARDS_DIR / "voice_pack_guard.py").exists()
        mark = "OK" if ok else "MISSING"
        print(f"  [{mark}] src/guards/voice_pack_guard.py")
        all_ok &= ok

        ok = (SRC_GUARDS_DIR / "meme_pack_guard.py").exists()
        mark = "OK" if ok else "MISSING"
        print(f"  [{mark}] src/guards/meme_pack_guard.py")
        all_ok &= ok

        # voice_packs
        vp = PROJECT_ROOT / "voice_packs"
        ok = vp.exists()
        mark = "OK" if ok else "MISSING"
        print(f"  [{mark}] voice_packs/ directory")
        all_ok &= ok

        if all_ok:
            print("\n  All checks passed. Ready to write.")
        else:
            print("\n  Some checks failed. Run install.bat first.")

        return 0 if all_ok else 1


def cmd_doctor(detail=True):
    """Alias for status with --detail by default."""
    return cmd_status(detail=detail)

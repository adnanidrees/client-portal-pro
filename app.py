import streamlit as st, yaml, os, datetime as dt, bcrypt
from yaml.loader import SafeLoader
from pathlib import Path

st.set_page_config(page_title="TickCom Client Portal", page_icon="🗝️", layout="wide")
st.title("🗝️ TickCom Client Portal")

# ---------- Safe rerun (new & old Streamlit compatible) ----------
def safe_rerun():
    try:
        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.experimental_rerun()
    except Exception:
        st.stop()

# ---------- Helpers ----------
def load_yaml(p, default):
    p = Path(p)
    if not p.exists(): return default
    with open(p, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=SafeLoader) or default

def save_yaml(p, data):
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

def expired(iso):
    if not iso: return False
    try:
        return dt.date.today() > dt.datetime.strptime(iso, "%Y-%m-%d").date()
    except:
        return False

users_cfg    = load_yaml("users.yaml",    {"credentials":{"users":[]}})
packages_cfg = load_yaml("packages.yaml", {"packages":{}})
tools_cfg    = load_yaml("tools.yaml",    {"tools":{}})

user_rows = users_cfg.get("credentials",{}).get("users", [])
if not user_rows:
    st.warning("⚠️ users.yaml me kam se kam ek user add karein."); st.stop()

def find_user(username):
    # case-insensitive, trimmed match
    uname = (username or "").strip().lower()
    for u in user_rows:
        if (u.get("username","").strip().lower() == uname):
            return u
    return None

def check_password(p_plain: str, p_hash: str) -> bool:
    try:
        # bcrypt hash (preferred)
        if (p_hash or "").startswith("$2"):
            return bcrypt.checkpw((p_plain or "").strip().encode("utf-8"),
                                  (p_hash or "").strip().encode("utf-8"))
        # fallback: allow plaintext (legacy/testing only)
        return (p_plain or "").strip() == (p_hash or "").strip()
    except Exception:
        return False

def login_form():
    st.subheader("Login")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Login")
    if ok:
        row = find_user(u)
        if row and row.get("password") and check_password(p, row["password"]):
            st.session_state["auth"] = True
            st.session_state["username"] = (u or "").strip()
            st.session_state["name"] = row.get("name", u)
            st.success("Logged in. Redirecting…")
            safe_rerun()
        else:
            st.error("Invalid username/password.")

# ---------- Auth ----------
if not st.session_state.get("auth"):
    login_form()
    st.stop()

username = st.session_state.get("username")
name     = st.session_state.get("name", username)
row      = find_user(username) or {}

# Suspend/expiry checks
if not row.get("active", True):
    st.error("Your account is inactive. Contact support."); st.stop()
if expired(row.get("expires_at")):
    st.error("Your subscription has expired. Contact billing."); st.stop()

# Logout
if st.sidebar.button("Logout"):
    st.session_state.clear()
    safe_rerun()
st.sidebar.success(f"Logged in as {name}")

# ---------- Tools visible ----------
st.subheader("Your Tools")
allowed = list(row.get("allowed_tools") or [])
pkg = row.get("package")
if pkg and pkg in packages_cfg.get("packages", {}):
    allowed = list(set(allowed) | set(packages_cfg["packages"][pkg]))

tools = tools_cfg.get("tools", {})
if not allowed:
    st.info("No tools assigned to your account yet.")
else:
    cols = st.columns(3)
    i = 0
    for key in allowed:
        info = tools.get(key)
        if not info: continue
        with cols[i % 3]:
            st.markdown(f"### {info.get('name', key)}")
            st.caption(info.get("desc",""))
            url = info.get("url")
            if url:
                st.link_button("Open", url, type="primary", use_container_width=True)
            else:
                st.button("URL missing", disabled=True, use_container_width=True)
        i += 1

st.divider()
st.write(f"**Package:** {pkg or '—'}  |  **Active:** {row.get('active', True)}  |  **Expires:** {row.get('expires_at') or '—'}")

# ---------- Admin Panel ----------
admins = [x.strip() for x in os.getenv("ADMIN_USERS","owner").split(",") if x.strip()]
if username in admins:
    st.markdown("---")
    st.subheader("🛠️ Admin Panel")
    table = []
    for r in user_rows:
        table.append({
            "username":    r.get("username",""),
            "name":        r.get("name",""),
            "package":     r.get("package",""),
            "allowed_tools": ", ".join(r.get("allowed_tools",[])),
            "active":      bool(r.get("active", True)),
            "expires_at":  r.get("expires_at","")
        })
    edited = st.data_editor(table, num_rows="dynamic", use_container_width=True, key="users_table")
    if st.button("💾 Save users.yaml"):
        new_users = []
        for r in edited:
            atools = [t.strip() for t in (r.get("allowed_tools","") or "").split(",") if t.strip()]
            old = find_user(r["username"]) or {}
            new_users.append({
                "username":    r["username"],
                "name":        r.get("name") or r["username"],
                "password":    old.get("password",""),   # password preserve
                "package":     r.get("package") or None,
                "allowed_tools": atools,
                "active":      bool(r.get("active", True)),
                "expires_at":  r.get("expires_at") or None
            })
        users_cfg["credentials"]["users"] = new_users
        save_yaml("users.yaml", users_cfg)
        st.success("Saved. Reload to apply.")

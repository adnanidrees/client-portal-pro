
import streamlit as st, yaml, os, datetime as dt
import streamlit_authenticator as stauth
from yaml.loader import SafeLoader
from pathlib import Path

st.set_page_config(page_title="TickCom Client Portal", page_icon="🗝️", layout="wide")
st.title("🗝️ TickCom Client Portal")

def load_yaml(p, default):
    p = Path(p)
    if not p.exists(): return default
    with open(p, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=SafeLoader) or default

def save_yaml(p, data):
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

users_cfg = load_yaml("users.yaml", {"credentials":{"users":[]}})
packages_cfg = load_yaml("packages.yaml", {"packages":{}})
tools_cfg = load_yaml("tools.yaml", {"tools":{}})

def to_auth_config(users_list):
    um, extra = {}, {}
    for u in users_list:
        um[u["username"]] = {"name": u.get("name", u["username"]), "password": u.get("password","")}
        extra[u["username"]] = {
            "package": u.get("package"),
            "allowed_tools": u.get("allowed_tools", []),
            "active": bool(u.get("active", True)),
            "expires_at": u.get("expires_at")
        }
    return {"credentials":{"usernames": um}}, extra

auth_cfg, extras = to_auth_config(users_cfg.get("credentials",{}).get("users", []))
if not auth_cfg["credentials"]["usernames"]:
    st.warning("⚠️ Add a user in users.yaml"); st.stop()

authenticator = stauth.Authenticate(
    auth_cfg["credentials"],
    cookie_name="tickcom_portal",
    cookie_key=os.getenv("PORTAL_COOKIE_KEY","supersecret"),
    cookie_expiry_days=14
)
# ---- Compatible login call (handles multiple authenticator versions) ----
try:
    login_result = authenticator.login("Login", location="main")
except TypeError:
    # older versions expect positional 'location'
    login_result = authenticator.login("Login", "main")

# Unpack flexibly (some versions return 3-tuple, some 2-tuple or dict)
name = None
auth_status = None
username = None

if isinstance(login_result, tuple):
    if len(login_result) == 3:
        name, auth_status, username = login_result
    elif len(login_result) == 2:
        name, auth_status = login_result
else:
    # possible dict shape
    try:
        name = login_result.get("name")
        auth_status = login_result.get("authentication_status") or login_result.get("status")
        username = login_result.get("username")
    except Exception:
        pass
# ------------------------------------------------------------------------


def expired(iso):
    if not iso: return False
    try:
        return dt.date.today() > dt.datetime.strptime(iso, "%Y-%m-%d").date()
    except: return False

if auth_status is False:
    st.error("Bad credentials.")
elif auth_status is None:
    st.info("Enter your credentials.")
else:
    u = extras.get(username, {})
    if not u.get("active", True): st.error("Account inactive."); st.stop()
    if expired(u.get("expires_at")): st.error("Subscription expired."); st.stop()

    authenticator.logout("Logout", "sidebar")
    st.sidebar.success(f"Logged in as {name}")
    allowed = list(u.get("allowed_tools") or [])
    pkg = u.get("package")
    if pkg and pkg in packages_cfg.get("packages", {}):
        allowed = list(set(allowed) | set(packages_cfg["packages"][pkg]))
    tools = tools_cfg.get("tools", {})
    st.subheader("Your Tools")
    cols = st.columns(3)
    i=0
    for key in allowed:
        info = tools.get(key); 
        if not info: continue
        with cols[i%3]:
            st.markdown(f"### {info.get('name', key)}")
            st.caption(info.get("desc",""))
            url = info.get("url")
            if url: st.link_button("Open", url, type="primary", use_container_width=True)
            else: st.button("URL missing", disabled=True, use_container_width=True)
        i+=1
    st.divider()
    st.write(f"**Active:** {u.get('active', True)} | **Expires:** {u.get('expires_at') or '—'}")

    admins = [x.strip() for x in os.getenv("ADMIN_USERS","").split(",") if x.strip()]
    if username in admins:
        st.subheader("🛠️ Admin Panel")
        table=[]
        for row in users_cfg.get("credentials",{}).get("users", []):
            table.append({"username":row["username"],"name":row.get("name",""),
                          "package":row.get("package",""),
                          "allowed_tools": ", ".join(row.get("allowed_tools",[])),
                          "active": bool(row.get("active", True)),
                          "expires_at": row.get("expires_at","")})
        df = st.data_editor(table, num_rows="dynamic", use_container_width=True, key="users_table")
        if st.button("💾 Save users.yaml"):
            new=[]
            for r in df:
                at=[t.strip() for t in (r.get("allowed_tools","") or "").split(",") if t.strip()]
                old = next((x for x in users_cfg["credentials"]["users"] if x["username"]==r["username"]), None)
                new.append({"username":r["username"],"name":r.get("name") or r["username"],
                            "password":(old or {}).get("password",""),
                            "package":r.get("package") or None,
                            "allowed_tools": at, "active": bool(r.get("active", True)),
                            "expires_at": r.get("expires_at") or None})
            users_cfg["credentials"]["users"]=new
            save_yaml("users.yaml", users_cfg)
            st.success("Saved. Reload to apply.")

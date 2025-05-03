# streamlit_app.py
import os
import textwrap
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import json
from datetime import datetime
from openai import OpenAI

# -----------------------------------------------------------------------------
# 1.  Session-state helpers
# -----------------------------------------------------------------------------
if "nodes" not in st.session_state:
    st.session_state.nodes: list[Node] = []
if "edges" not in st.session_state:
    st.session_state.edges: list[Edge] = []
if "last_id" not in st.session_state:
    st.session_state.last_id: int = 0

# 1-bis.  Extra session-state helpers
if "actions" not in st.session_state:
    st.session_state.actions: list[dict] = []
if "user_ids" not in st.session_state:
    st.session_state.user_ids: list[int] = []
if "account_ids" not in st.session_state:
    st.session_state.account_ids: list[str] = []
if "request_ids" not in st.session_state:
    st.session_state.request_ids: list[int] = []
if "editing_modal" not in st.session_state:
    st.session_state.editing_modal = False
# track the last graph-node click so we only open on a new click
if "last_graph_click" not in st.session_state:
    st.session_state.last_graph_click = None

def next_id() -> int:
    st.session_state.last_id += 1
    return st.session_state.last_id

def cancel_edit():
    st.session_state.edit_node_id = None
    st.session_state.editing_modal = False

# -----------------------------------------------------------------------------
# Helper ➊ – append one action and draw its node
# -----------------------------------------------------------------------------

# Validation schema for AI-generated actions  –  key → expected Python type
ACTION_SCHEMA: dict[str, dict[str, type | tuple[type, ...]]] = {
    "CreateUserPerson":         {"user_id": int},
    "CreateMonetaryAccount":    {
        "user_id": int,
        "account_id": str,
        "currency": str,
        "daily_limit_value": (int, float),
    },
    "GetAccountOverview":       {"account_id": str},
    "MakePayment":              {
        "user_id": int,
        "account_id": str,
        "amount_value": (int, float),
        "amount_currency": str,
        "counterparty_account_id": str,
    },
    "RequestPayment":           {
        "user_id": int,
        "account_id": str,
        "amount_value": (int, float),
        "amount_currency": str,
        "counterparty_account_id": str,
        "expiry_date": int,
        "request_response_id": int,
    },
    "RespondToPaymentRequest":  {
        "user_id": int,
        "account_id": str,
        "request_response_id": int,
        "status": str,
    },
    "ListPayments":             {"user_id": int, "account_id": str},
}

def validate_action_schema(action: dict) -> None:
    """Raise ValueError if action is missing fields or has wrong types."""
    a_type = action.get("action_type")
    if a_type not in ACTION_SCHEMA:
        raise ValueError(f"Unknown action_type: {a_type}")

    schema = ACTION_SCHEMA[a_type]
    for key, expected in schema.items():
        if key not in action:
            raise ValueError(f"{a_type}: missing key '{key}'")
        if not isinstance(action[key], expected):
            raise ValueError(
                f"{a_type}.{key} expected {expected}, got {type(action[key]).__name__}"
            )

def add_action_to_sequence(action: dict):
    """
    Append `action` to the global sequence, update all bookkeeping helpers
    (user_ids, account_ids, request_ids) and extend the graph so the new node
    is chained after the last one.
    """
    action_type = action["action_type"]
    node_id = str(next_id())
    label   = action_type
    shape   = "ellipse"          # default

    # ---- per-type tweaks ----
    if action_type == "CreateUserPerson":
        uid = action.get("user_id", len(st.session_state.user_ids) + 1)
        action["user_id"] = uid
        if uid not in st.session_state.user_ids:
            st.session_state.user_ids.append(uid)
        label = f"{action_type} (u{uid})"
        shape = "box"

    elif action_type == "CreateMonetaryAccount":
        acc = action["account_id"]
        if acc not in st.session_state.account_ids:
            st.session_state.account_ids.append(acc)
        label = f"{action_type} (acc {acc})"

    elif action_type == "GetAccountOverview":
        label = f"{action_type} (acc {action['account_id']})"

    elif action_type == "MakePayment":
        label = (
            f"{action_type} ({action['amount_value']} "
            f"{action['amount_currency']} → {action['counterparty_account_id']})"
        )

    elif action_type == "RequestPayment":
        req = action["request_response_id"]
        if req not in st.session_state.request_ids:
            st.session_state.request_ids.append(req)
        label = f"{action_type} (req {req})"

    elif action_type == "RespondToPaymentRequest":
        label = f"{action_type} ({action['status']})"
        shape = "box"

    elif action_type == "ListPayments":
        label = f"{action_type} (acc {action['account_id']})"

    # ---- store & draw ----
    st.session_state.actions.append(action)
    st.session_state.nodes.append(Node(id=node_id, label=label, shape=shape))
    if len(st.session_state.nodes) > 1:
        st.session_state.edges.append(
            Edge(st.session_state.nodes[-2].id, node_id)
        )

# -----------------------------------------------------------------------------
# 3.  Draw the graph and let the user connect nodes
# -----------------------------------------------------------------------------
st.title("Bunq sandbox flow-chart builder")

# Configuration for graph
config = Config(
    width=700,
    height=500,
    directed=True,
    nodeHighlightBehavior=True,
    highlightColor="#F7A7A6",
    collapsible=True,
)

# Draw the graph
try:
    selected = agraph(
        nodes=st.session_state.nodes,
        edges=st.session_state.edges,
        config=config,
    )

    # handle newly added edges
    if isinstance(selected, dict) and selected.get("addedEdges"):
        for e in selected["addedEdges"]:
            edge = Edge(source=str(e["source"]), target=str(e["target"]))
            if all(not (ed.source == edge.source and ed.target == edge.target)
                  for ed in st.session_state.edges):
                st.session_state.edges.append(edge)

    elif isinstance(selected, str):
        # only open the modal on a brand-new node click
        if selected != st.session_state.last_graph_click:
            st.session_state.edit_node_id = selected
            st.session_state.editing_modal = True
        # record the click for next rerun
        st.session_state.last_graph_click = selected

    else:
        # when nothing active AND not editing, clear selection
        if not st.session_state.editing_modal:
            st.session_state.edit_node_id = None

except Exception as e:
    st.error(f"Graph rendering error: {e}")
    st.session_state.edit_node_id = None

# Check edit state
edit_id = st.session_state.get("edit_node_id")
editing = edit_id is not None

# -----------------------------------------------------------------------------
# Edit Action Modal Dialog
# -----------------------------------------------------------------------------
if editing and st.session_state.editing_modal:
    try:
        idx = next(i for i, n in enumerate(st.session_state.nodes) if n.id == edit_id)
        current = st.session_state.actions[idx]
        action_type = current["action_type"]
        
        # Create a modal-like container for editing
        edit_col1, edit_col2, edit_col3 = st.columns([1, 3, 1])
        
        with edit_col2:
            st.markdown("""
            <style>
            .edit-card {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                background-color: white;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                margin: 10px 0;
            }
            </style>
            """, unsafe_allow_html=True)
            
            with st.container():
                st.markdown(f'<div class="edit-card">', unsafe_allow_html=True)
                st.subheader(f"Edit Action: {action_type}")
                st.markdown(f"Action #{idx}")
                
                params = {}  # will hold the updated fields
                
                # Different form fields based on action type
                if action_type == "CreateUserPerson":
                    st.info("This action cannot be edited.")
                
                elif action_type == "CreateMonetaryAccount":
                    if "user_id" in current and current["user_id"] in st.session_state.user_ids:
                        user_idx = st.session_state.user_ids.index(current["user_id"])
                    else:
                        user_idx = 0
                    
                    owner = st.selectbox("Owner (user_id)", st.session_state.user_ids, index=user_idx)
                    
                    currency_opts = ("EUR", "USD", "GBP", "CHF", "JPY")
                    if "currency" in current and current["currency"] in currency_opts:
                        curr_idx = currency_opts.index(current["currency"])
                    else:
                        curr_idx = 0
                    
                    currency = st.selectbox("Currency", currency_opts, index=curr_idx)
                    # Make sure *value* and *step* are both floats to avoid
                    # "All numerical arguments must be of the same type" error.
                    daily_limit_default = float(current.get("daily_limit_value", 1000.00))
                    daily_limit = st.number_input(
                        "Daily limit value",
                        0.00,
                        step=0.01,
                        value=daily_limit_default,
                    )
                    params.update(
                        user_id=owner,
                        account_id=current["account_id"],  # Keep the same account ID
                        currency=currency,
                        daily_limit_value=daily_limit,
                    )
                
                elif action_type == "GetAccountOverview":
                    if "account_id" in current and current["account_id"] in st.session_state.account_ids:
                        acc_idx = st.session_state.account_ids.index(current["account_id"])
                    else:
                        acc_idx = 0
                    
                    acc = st.selectbox("account_id", st.session_state.account_ids, index=acc_idx)
                    params.update(account_id=acc)
                
                elif action_type == "MakePayment":
                    if "user_id" in current and current["user_id"] in st.session_state.user_ids:
                        user_idx = st.session_state.user_ids.index(current["user_id"])
                    else:
                        user_idx = 0
                    
                    if "account_id" in current and current["account_id"] in st.session_state.account_ids:
                        acc_idx = st.session_state.account_ids.index(current["account_id"])
                    else:
                        acc_idx = 0
                        
                    if "counterparty_account_id" in current and current["counterparty_account_id"] in st.session_state.account_ids:
                        cpty_idx = st.session_state.account_ids.index(current["counterparty_account_id"])
                    else:
                        cpty_idx = 0
                        
                    currency_opts = ("EUR", "USD", "GBP")
                    if "amount_currency" in current and current["amount_currency"] in currency_opts:
                        curr_idx = currency_opts.index(current["amount_currency"])
                    else:
                        curr_idx = 0
                    
                    owner = st.selectbox("user_id (sender)", st.session_state.user_ids, index=user_idx)
                    src_acc = st.selectbox("account_id (source)", st.session_state.account_ids, index=acc_idx)
                    amount = st.number_input("amount_value", 0.00, step=0.01, value=current.get("amount_value", 10.00))
                    currency = st.selectbox("amount_currency", currency_opts, index=curr_idx)
                    counterparty = st.selectbox("counterparty_account_id", st.session_state.account_ids, index=cpty_idx)
                    
                    params.update(
                        user_id=owner,
                        account_id=src_acc,
                        amount_value=amount,
                        amount_currency=currency,
                        counterparty_account_id=counterparty,
                    )
                
                # ---------- RequestPayment (NEW edit support) ----------
                elif action_type == "RequestPayment":
                    # Pre-select indices for dropdowns
                    user_idx = (
                        st.session_state.user_ids.index(current["user_id"])
                        if current.get("user_id") in st.session_state.user_ids
                        else 0
                    )
                    acc_idx = (
                        st.session_state.account_ids.index(current["account_id"])
                        if current.get("account_id") in st.session_state.account_ids
                        else 0
                    )
                    cpty_options = ["sugardaddy"] + st.session_state.account_ids
                    cpty_idx = (
                        cpty_options.index(current["counterparty_account_id"])
                        if current.get("counterparty_account_id") in cpty_options
                        else 0
                    )
                    currency_opts = ("EUR", "USD", "GBP")
                    curr_idx = (
                        currency_opts.index(current["amount_currency"])
                        if current.get("amount_currency") in currency_opts
                        else 0
                    )

                    owner   = st.selectbox("user_id (receiver)", st.session_state.user_ids, index=user_idx)
                    acc_rcv = st.selectbox("account_id (receiver)", st.session_state.account_ids, index=acc_idx)
                    amount  = st.number_input(
                        "amount_value",
                        0.00,
                        step=0.01,
                        value=current.get("amount_value", 25.00),
                    )
                    currency = st.selectbox("amount_currency", currency_opts, index=curr_idx)
                    counterparty = st.selectbox("counterparty_account_id", cpty_options, index=cpty_idx)
                    expiry_default = int(current.get("expiry_date", int(datetime.utcnow().timestamp()) + 7200))
                    expiry = st.number_input(
                        "expiry_date (epoch‐secs)",
                        value=expiry_default,
                        step=1,          # int step → keeps types consistent
                        format="%d",
                    )

                    params.update(
                        user_id=owner,
                        account_id=acc_rcv,
                        amount_value=amount,
                        amount_currency=currency,
                        counterparty_account_id=counterparty,
                        expiry_date=expiry,
                        request_response_id=current["request_response_id"],
                    )
                
                # Other action types follow similar patterns...
                # Add your other action types here
                
                # Save and cancel buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Save Changes", key=f"save_{idx}"):
                        if params:  # Only update if there are parameters to update
                            # Update action
                            st.session_state.actions[idx] = {"action_type": action_type, **params}
                            
                            # Update node label
                            node = st.session_state.nodes[idx]
                            
                            if action_type == "CreateUserPerson":
                                pass  # No editable fields
                            elif action_type == "CreateMonetaryAccount":
                                node.label = f"{action_type} (acc {current['account_id']})"
                            elif action_type == "GetAccountOverview":
                                node.label = f"{action_type} (acc {params['account_id']})"
                            elif action_type == "MakePayment":
                                node.label = f"{action_type} ({params['amount_value']} {params['amount_currency']} → {params['counterparty_account_id']})"
                            elif action_type == "RequestPayment":
                                node.label = f"{action_type} (req {params['request_response_id']})"
                            # Update other action types accordingly
                            
                            st.session_state.nodes[idx] = node
                            
                        # Close modal cleanly (don't trigger "just_cancelled")
                        st.session_state.edit_node_id = None
                        st.session_state.editing_modal = False
                        st.session_state.just_cancelled = False
                        st.rerun()
                        
                with col2:
                    if st.button("❌ Cancel", key=f"cancel_{idx}"):
                        cancel_edit()
                        st.rerun()
                        
                st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error in edit mode: {str(e)}")
        cancel_edit()

# -----------------------------------------------------------------------------
# File Upload / Download for action scenarios
# -----------------------------------------------------------------------------
# Provide controls in the sidebar to load an existing scenario from a JSON file
# and to download the current sequence as JSON.

st.sidebar.markdown("### 📂 Load / Save scenario")

uploaded_file = st.sidebar.file_uploader("Load JSON scenario", type=["json"], key="uploader")
if uploaded_file is not None:
    try:
        # Decode bytes to string and parse JSON
        raw_json = uploaded_file.getvalue().decode("utf-8")
        loaded_actions = json.loads(raw_json)
        # Accept a single dict or a list as valid payload
        if isinstance(loaded_actions, dict):
            loaded_actions = [loaded_actions]

        # --- Reset all graph-related session state ---
        st.session_state.actions.clear()
        st.session_state.nodes.clear()
        st.session_state.edges.clear()
        st.session_state.user_ids.clear()
        st.session_state.account_ids.clear()
        st.session_state.request_ids.clear()
        st.session_state.last_id = 0

        # Validate & rebuild graph
        for action in loaded_actions:
            validate_action_schema(action)
            add_action_to_sequence(action)

        st.success("✅ Scenario loaded!")
        st.experimental_rerun()
    except Exception as e:
        st.sidebar.error(f"Failed to load JSON: {e}")

# Download button for the current scenario
st.sidebar.download_button(
    label="💾 Download current scenario",
    data=json.dumps(st.session_state.actions, indent=2),
    file_name="actions.json",
    mime="application/json",
)

# -----------------------------------------------------------------------------
# 2.  Sidebar: build the *sequence* of actions
# -----------------------------------------------------------------------------
st.sidebar.subheader("Add action" if not editing else "Edit in progress...")

if not editing:
    action_type = st.sidebar.selectbox(
        "Action type",
        (
            "CreateUserPerson",
            "CreateMonetaryAccount",
            "GetAccountOverview",
            "MakePayment",
            "RequestPayment",
            "RespondToPaymentRequest",
            "ListPayments",
        ),
    )

    params = {}  # will hold the fields for the JSON action

    # ---------- CreateUserPerson ----------
    if action_type == "CreateUserPerson":
        # no input fields; auto-generate a new user ID
        if st.sidebar.button("Add action"):
            new_user_id = len(st.session_state.user_ids) + 1
            st.session_state.user_ids.append(new_user_id)

            # only send back action_type + user_id
            st.session_state.actions.append({
                "action_type": action_type,
                "user_id": new_user_id,
            })

            # add a node labeled with the generated user ID
            node_id = str(next_id())
            st.session_state.nodes.append(
                Node(id=node_id, label=f"{action_type} (u{new_user_id})", shape="box")
            )
            if len(st.session_state.nodes) > 1:  # chain arrow
                st.session_state.edges.append(
                    Edge(st.session_state.nodes[-2].id, node_id)
                )
            
            st.rerun()

    # ---------- CreateMonetaryAccount ----------
    elif action_type == "CreateMonetaryAccount":
        if not st.session_state.user_ids:
            st.sidebar.info("⚠️  Create a user first.")
        else:
            owner = st.sidebar.selectbox("Owner (user_id)", st.session_state.user_ids)
            currency = st.sidebar.selectbox("Currency", ("EUR", "USD", "GBP", "CHF", "JPY"))
            daily_limit = st.sidebar.number_input("Daily limit value", 0.00, step=0.01, value=1000.00)
            if st.sidebar.button("Add action"):
                new_acc_id = chr(ord("A") + len(st.session_state.account_ids))
                st.session_state.account_ids.append(new_acc_id)

                params.update(
                    user_id=owner,
                    account_id=new_acc_id,
                    currency=currency,
                    daily_limit_value=daily_limit,
                )
                st.session_state.actions.append({"action_type": action_type, **params})

                node_id = str(next_id())
                st.session_state.nodes.append(Node(id=node_id, label=f"{action_type} (acc {new_acc_id})", shape="ellipse"))
                if len(st.session_state.nodes) > 1:
                    st.session_state.edges.append(Edge(st.session_state.nodes[-2].id, node_id))
                
                st.rerun()

    # ---------- GetAccountOverview ----------
    elif action_type == "GetAccountOverview":
        if not st.session_state.account_ids:
            st.sidebar.info("⚠️  No account yet.")
        else:
            acc = st.sidebar.selectbox("account_id", st.session_state.account_ids)
            if st.sidebar.button("Add action"):
                params.update(account_id=acc)
                st.session_state.actions.append({"action_type": action_type, **params})

                node_id = str(next_id())
                st.session_state.nodes.append(
                    Node(
                        id=node_id,
                        label=f"{action_type} (acc {acc})",
                        shape="ellipse",
                    )
                )
                if len(st.session_state.nodes) > 1:
                    st.session_state.edges.append(Edge(st.session_state.nodes[-2].id, node_id))
                
                st.rerun()

    # ---------- MakePayment ----------
    elif action_type == "MakePayment":
        if not st.session_state.account_ids:
            st.sidebar.info("⚠️  Need an account first.")
        else:
            owner = st.sidebar.selectbox("user_id (sender)", st.session_state.user_ids)
            src_acc = st.sidebar.selectbox("account_id (source)", st.session_state.account_ids)
            amount = st.sidebar.number_input("amount_value", 0.00, step=0.01, value=10.00)
            currency = st.sidebar.selectbox("amount_currency", ("EUR", "USD", "GBP"))
            counterparty = st.sidebar.selectbox("counterparty_account_id", st.session_state.account_ids)
            if st.sidebar.button("Add action"):
                params.update(
                    user_id=owner,
                    account_id=src_acc,
                    amount_value=amount,
                    amount_currency=currency,
                    counterparty_account_id=counterparty,
                )
                st.session_state.actions.append({"action_type": action_type, **params})

                node_id = str(next_id())
                st.session_state.nodes.append(
                    Node(
                        id=node_id,
                        label=f"{action_type} ({amount} {currency} → {counterparty})",
                        shape="ellipse",
                    )
                )
                if len(st.session_state.nodes) > 1:
                    st.session_state.edges.append(Edge(st.session_state.nodes[-2].id, node_id))
                st.rerun()

    # ---------- RequestPayment ----------
    elif action_type == "RequestPayment":
        if not st.session_state.account_ids:
            st.sidebar.info("⚠️  Need an account first.")
        else:
            owner   = st.sidebar.selectbox("user_id (receiver)", st.session_state.user_ids)
            acc_rcv = st.sidebar.selectbox("account_id (receiver)", st.session_state.account_ids)
            amount  = st.sidebar.number_input("amount_value", 0.00, step=0.01, value=25.00)
            currency= st.sidebar.selectbox("amount_currency", ("EUR", "USD", "GBP"))
            counterparty = st.sidebar.selectbox(
                "counterparty_account_id",
                ["sugardaddy"] + st.session_state.account_ids
            )
            expiry  = st.sidebar.number_input(
                "expiry_date (epoch‐secs)",
                int(datetime.utcnow().timestamp()) + 7200
            )
            if st.sidebar.button("Add action"):
                new_req_id = len(st.session_state.request_ids) + 1
                st.session_state.request_ids.append(new_req_id)
                params.update(
                    user_id=owner,
                    account_id=acc_rcv,
                    amount_value=amount,
                    amount_currency=currency,
                    counterparty_account_id=counterparty,
                    expiry_date=expiry,
                    request_response_id=new_req_id,
                )
                st.session_state.actions.append({"action_type": action_type, **params})

                node_id = str(next_id())
                st.session_state.nodes.append(
                    Node(id=node_id, label=f"{action_type} (req {new_req_id})", shape="ellipse")
                )
                if len(st.session_state.nodes) > 1:
                    st.session_state.edges.append(Edge(st.session_state.nodes[-2].id, node_id))
                st.rerun()

    # ---------- RespondToPaymentRequest ----------
    elif action_type == "RespondToPaymentRequest":
        if not st.session_state.request_ids:
            st.sidebar.info("⚠️  No request to answer.")
        else:
            owner = st.sidebar.selectbox("user_id", st.session_state.user_ids)
            acc   = st.sidebar.selectbox("account_id", st.session_state.account_ids)
            req   = st.sidebar.selectbox("request_response_id", st.session_state.request_ids)
            status= st.sidebar.selectbox("status", ("ACCEPTED", "REJECTED"))
            if st.sidebar.button("Add action"):
                params.update(
                    user_id=owner,
                    account_id=acc,
                    request_response_id=req,
                    status=status,
                )
                st.session_state.actions.append({"action_type": action_type, **params})

                node_id = str(next_id())
                st.session_state.nodes.append(
                    Node(id=node_id, label=f"{action_type} ({status})", shape="box")
                )
                if len(st.session_state.nodes) > 1:
                    st.session_state.edges.append(Edge(st.session_state.nodes[-2].id, node_id))
                st.rerun()

    # ---------- ListPayments ----------
    elif action_type == "ListPayments":
        if not st.session_state.account_ids:
            st.sidebar.info("⚠️  Need an account first.")
        else:
            owner = st.sidebar.selectbox("user_id", st.session_state.user_ids)
            acc   = st.sidebar.selectbox("account_id", st.session_state.account_ids)
            if st.sidebar.button("Add action"):
                params.update(user_id=owner, account_id=acc)
                st.session_state.actions.append({"action_type": action_type, **params})

                node_id = str(next_id())
                st.session_state.nodes.append(
                    Node(id=node_id, label=f"{action_type} (acc {acc})", shape="ellipse")
                )
                if len(st.session_state.nodes) > 1:
                    st.session_state.edges.append(Edge(st.session_state.nodes[-2].id, node_id))
                st.rerun()

# -----------------------------------------------------------------------------
# 4.  DEPLOY   (replaces "Generate bunq-SDK code")
# -----------------------------------------------------------------------------
st.markdown("### Action sequence")
st.json(st.session_state.actions)


# 4-ter.  🤖 AI helper – Ask or Generate
# -----------------------------------------------------------------------------
st.markdown("## 🤖 Ask the LLM **or** generate new actions")

with st.form("ai_tools_form"):
    ai_query = st.text_area("Describe what you need (question or flow specification)")
    col_ask, col_gen = st.columns(2)
    ask_clicked  = col_ask.form_submit_button("📤 Ask LLM")
    gen_clicked  = col_gen.form_submit_button("✨ Generate actions")

if ask_clicked and ai_query.strip():
    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="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",
        )
        system_prompt = (
            "You are an expert Bunq-sandbox assistant.\n"
            "Here is the current action sequence:\n\n"
            f"{json.dumps(st.session_state.actions, indent=2)}\n\n"
            "Answer the user's question briefly."
        )
        resp = client.chat.completions.create(
            model="qwen/qwq-32b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": ai_query},
            ],
            temperature=0.5,
            top_p=0.7,
            max_tokens=1024,
        )
        answer = resp.choices[0].message.content
        if "</think>" in answer:
            answer = answer.split("</think>")[1]
        st.success("LLM answer:")
        st.markdown(answer)

    except Exception as e:
        st.error(f"Error querying LLM: {e}")

elif gen_clicked and ai_query.strip():
    # Concise schema-based prompt so model replies with strict JSON

    # ─── edit: make ACTION_SCHEMA JSON-safe (types → their __name__) ───
    schema_for_prompt = {
        action_type: {
            field: (
                typ.__name__
                if isinstance(typ, type)
                else [t.__name__ for t in typ]
            )
            for field, typ in fields.items()
        }
        for action_type, fields in ACTION_SCHEMA.items()
    }
    schema_str = json.dumps(schema_for_prompt, indent=2)
    # ─────────────────────────────────────────────────────────────────────

    gen_system_prompt = textwrap.dedent(f"""
    You are an expert Bunq-sandbox assistant.  
    Your task is to translate the USER'S high-level description of a flow into a
    STRICT, machine-readable JSON array of **actions**.

    ╔════════════════════════════════════════════════════════════════════╗
    ║ 1.  OUTPUT FORMAT (NO prose!)                                      ║
    ╚════════════════════════════════════════════════════════════════════╝
    • Return **only** a JSON array (not inside markdown).  
      ‣ Example (minimal):  
        [
          {{"action_type": "CreateUserPerson", "user_id": 1}},
          {{"action_type": "CreateMonetaryAccount", "user_id": 1,
            "account_id": "A", "currency": "EUR", "daily_limit_value": 1000}}
        ]
    • Do NOT add any extra keys, comments, or explanatory text.
    • Use numbers for numeric fields (no quotes).

    ╔════════════════════════════════════════════════════════════════════╗
    ║ 2.  ALLOWED ACTION TYPES & REQUIRED FIELDS                         ║
    ╚════════════════════════════════════════════════════════════════════╝
    {schema_str}

    ╔════════════════════════════════════════════════════════════════════╗
    ║ 3.  CONSISTENCY RULES                                              ║
    ╚════════════════════════════════════════════════════════════════════╝
    • user_id, account_id, request_response_id must be internally
      consistent and unique unless the user explicitly asks to reuse one.  
        ‣ New users: increment 1, 2, 3…  
        ‣ New accounts: "A", "B", "C"… in the order they are created.  
        ‣ New request_response_id: increment 1, 2, 3…
    • A later action may reference IDs created earlier in the same list.

    ╔════════════════════════════════════════════════════════════════════╗
    ║ 4.  RESPONSE STRATEGY                                              ║
    ╚════════════════════════════════════════════════════════════════════╝
    1. Think silently how to satisfy the request and build a VALID sequence.  
    2. Respond **only** with the JSON array that passes the schema above.  
    """)
    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="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",
        )
        resp = client.chat.completions.create(
            model="qwen/qwq-32b",
            messages=[
                {"role": "system", "content": gen_system_prompt},
                {"role": "user",   "content": ai_query},
            ],
            temperature=0.3,
            top_p=0.7,
            max_tokens=30960 ,
        )
        raw = resp.choices[0].message.content
        if "</think>" in raw:
            raw = raw.split("</think>")[1]

        candidate = json.loads(raw)
        if isinstance(candidate, dict):
            candidate = [candidate]

        # --- strict validation ---
        for a in candidate:
            validate_action_schema(a)

        # --- everything OK → add to graph ---
        for a in candidate:
            add_action_to_sequence(a)

        st.success("✅ Actions generated & added to graph!")
        st.rerun()

    except (json.JSONDecodeError, ValueError) as e:
        # Print a full traceback and raw LLM payload to the server console for debugging
        import traceback
        print("❗️Error validating LLM-generated actions:")
        traceback.print_exc()
        print("Raw LLM output:", raw)
        # Still show a concise error in the Streamlit UI
        st.error(f"⚠️ Invalid output from LLM:\n\n{e}")
    except Exception as e:
        st.error(f"Error generating actions: {e}")

def deploy(actions: list[dict]):
    """
    Start the interpreter in a background thread, stream its log messages,
    and display them in the Streamlit app.
    """
    import queue
    import threading
    # TODO: adjust this import to point at your actual interpreter
    from interpret import BunqInterpreter

    msg_queue = queue.Queue()
    interpreter = BunqInterpreter()
    thread = threading.Thread(
        target=lambda: interpreter.interpret(actions, msg_queue),
        daemon=True,
    )
    thread.start()

    # prepare sidebar log area
    logs = []
    log_placeholder = st.sidebar.empty()
    st.sidebar.info("🔄 Interpreter started…")

    # pull messages from the queue and append to the sidebar text_area
    while True:
        try:
            msg = msg_queue.get(timeout=0.5)
            logs.append(msg)
            log_placeholder.text_area("🛠️ Debug log", "\n".join(logs), height=300)
        except queue.Empty:
            if not thread.is_alive():
                break

    st.sidebar.success("✅ Interpreter finished processing actions!")

if st.button("Deploy ▶︎"):
    deploy(st.session_state.actions)

# -----------------------------------------------------------------------------
# 5.  Tiny footer
# -----------------------------------------------------------------------------
st.markdown(
    """
    ---
    *Made with [streamlit-agraph](https://github.com/ChrisDelClea/streamlit-agraph)
    on the bunq sandbox.*
    """
)
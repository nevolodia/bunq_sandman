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
                    daily_limit = st.number_input("Daily limit value", 0.00, step=0.01, 
                                                value=current.get("daily_limit_value", 1000.00))
                    params.update(
                        user_id=owner,
                        account_id=current["account_id"],  # Keep the same account ID
                        currency=currency,
                        daily_limit_value=daily_limit,
                    )
                
                elif action_type == "GetAccountOverview":
                    if "monetary_account_id" in current and current["monetary_account_id"] in st.session_state.account_ids:
                        acc_idx = st.session_state.account_ids.index(current["monetary_account_id"])
                    else:
                        acc_idx = 0
                    
                    acc = st.selectbox("monetary_account_id", st.session_state.account_ids, index=acc_idx)
                    params.update(monetary_account_id=acc)
                
                elif action_type == "MakePayment":
                    if "user_id" in current and current["user_id"] in st.session_state.user_ids:
                        user_idx = st.session_state.user_ids.index(current["user_id"])
                    else:
                        user_idx = 0
                    
                    if "monetary_account_id" in current and current["monetary_account_id"] in st.session_state.account_ids:
                        acc_idx = st.session_state.account_ids.index(current["monetary_account_id"])
                    else:
                        acc_idx = 0
                        
                    if "counterparty_iban" in current and current["counterparty_iban"] in st.session_state.account_ids:
                        cpty_idx = st.session_state.account_ids.index(current["counterparty_iban"])
                    else:
                        cpty_idx = 0
                        
                    currency_opts = ("EUR", "USD", "GBP")
                    if "amount_currency" in current and current["amount_currency"] in currency_opts:
                        curr_idx = currency_opts.index(current["amount_currency"])
                    else:
                        curr_idx = 0
                    
                    owner = st.selectbox("user_id (sender)", st.session_state.user_ids, index=user_idx)
                    src_acc = st.selectbox("monetary_account_id (source)", st.session_state.account_ids, index=acc_idx)
                    amount = st.number_input("amount_value", 0.00, step=0.01, value=current.get("amount_value", 10.00))
                    currency = st.selectbox("amount_currency", currency_opts, index=curr_idx)
                    counterparty = st.selectbox("counterparty_iban", st.session_state.account_ids, index=cpty_idx)
                    
                    params.update(
                        user_id=owner,
                        monetary_account_id=src_acc,
                        amount_value=amount,
                        amount_currency=currency,
                        counterparty_iban=counterparty,
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
                                node.label = f"{action_type} (acc {params['monetary_account_id']})"
                            elif action_type == "MakePayment":
                                node.label = f"{action_type} ({params['amount_value']} {params['amount_currency']} → {params['counterparty_iban']})"
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
            acc = st.sidebar.selectbox("monetary_account_id", st.session_state.account_ids)
            if st.sidebar.button("Add action"):
                params.update(monetary_account_id=acc)
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
            src_acc = st.sidebar.selectbox("monetary_account_id (source)", st.session_state.account_ids)
            amount = st.sidebar.number_input("amount_value", 0.00, step=0.01, value=10.00)
            currency = st.sidebar.selectbox("amount_currency", ("EUR", "USD", "GBP"))
            # select one of your virtual accounts as counterparty
            counterparty = st.sidebar.selectbox(
                "counterparty_iban", st.session_state.account_ids
            )
            if st.sidebar.button("Add action"):
                params.update(
                    user_id=owner,
                    monetary_account_id=src_acc,
                    amount_value=amount,
                    amount_currency=currency,
                    counterparty_iban=counterparty,
                )
                st.session_state.actions.append({"action_type": action_type, **params})

                node_id = str(next_id())
                # explicit id/label so the text actually shows up
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

    # Add the remaining action types similarly
    # For brevity, I'm not including all of them here

# -----------------------------------------------------------------------------
# 4.  DEPLOY   (replaces "Generate bunq-SDK code")
# -----------------------------------------------------------------------------
st.markdown("### Action sequence")
st.json(st.session_state.actions)

# -----------------------------------------------------------------------------
# 4-bis.  Chat with LLM about the action sequence
# -----------------------------------------------------------------------------
st.markdown("## 💬 Ask the LLM about this flow")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# draw previous turns
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---- input box ----
user_input = st.chat_input("Ask anything about the action sequence…")

if user_input:
    # 1) append user's turn to history and echo it
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2) craft conversation for the LLM
    system_prompt = (
        "You are an expert Bunq-sandbox assistant.\n"
        "Here is the current action sequence the user built:\n\n"
        f"{json.dumps(st.session_state.actions, indent=2)}\n\n"
        "When you answer, be concise, and answer very shortly, using as least words as possible."
        "action indices (0-based) if you need to point to a particular step."
    )

    try:
        conversation = [{"role": "system", "content": system_prompt}]
        conversation.extend(st.session_state.chat_history)

        # 3) query the model
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="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",
        )
        resp = client.chat.completions.create(
            model="qwen/qwq-32b",
            messages=conversation,
            temperature=0.6,
            top_p=0.7,
            max_tokens=4096,
        )

        assistant_reply = resp.choices[0].message.content
        if "</think>" in assistant_reply:
            assistant_reply = assistant_reply.split("</think>")[1]

        # 4) show & save assistant reply
        with st.chat_message("assistant"):
            st.markdown(assistant_reply)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": assistant_reply}
        )
    except Exception as e:
        st.error(f"Error communicating with LLM: {str(e)}")

def deploy(actions: list[dict]):
    """
    Placeholder ‑ here you would start the interpreter thread
    and pass it `actions`.
    """
    st.success("🚀  Actions sent for deployment!")
    # For demo purposes just dump to file:
    with open("actions_run.json", "w") as fh:
        json.dump(actions, fh, indent=2)

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
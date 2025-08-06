import React, { useEffect, useState } from "react";
import { apiFetch } from "./api";
import { useAuth } from "./AuthProvider";

// PUBLIC_INTERFACE
export default function NotesDashboard() {
    const { token, logout } = useAuth();
    const [notes, setNotes] = useState([]);
    const [search, setSearch] = useState("");
    const [loading, setLoading] = useState(false);

    async function loadNotes(q) {
        setLoading(true);
        try {
            const n = await apiFetch(`/notes?search=${encodeURIComponent(q||"")}`, { token });
            setNotes(n);
        } catch (e) { console.error(e);}
        setLoading(false);
    }
    useEffect(() => { loadNotes(""); }, [token]);

    return (
        <div className="notes-dashboard">
            <div style={{display: "flex", justifyContent: "flex-end", gap: 8}}>
                <button onClick={logout}>Logout</button>
                <button onClick={() => window.location.reload()}>Reload</button>
            </div>
            <h2>Your Notes</h2>
            <input
                type="text"
                placeholder="Search notes"
                value={search}
                onChange={e => setSearch(e.target.value)}
                aria-label="Search notes"
                style={{padding: 4}}
                onKeyUp={e => e.key === "Enter" && loadNotes(search)}
            />
            <button onClick={() => loadNotes(search)}>Search</button>
            {loading ? <div>Loading...</div> : (
                <div>
                    {notes.length === 0 && <div>No notes found. Create one!</div>}
                    <ul>
                        {notes.map(n =>
                            <li key={n.id}>
                                <strong>{n.title}</strong>
                                <div style={{fontSize: "0.8em"}}>{new Date(n.timestamp).toLocaleString()}</div>
                            </li>
                        )}
                    </ul>
                </div>
            )}
        </div>
    );
}

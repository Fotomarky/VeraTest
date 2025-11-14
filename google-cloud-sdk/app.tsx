import React, { useState } from "react";
import { auth, provider, signInWithPopup, signOut } from "./firebase"; // Adjust path as needed

function App() {
  const [user, setUser] = useState(null);

  const handleLogin = async () => {
    const result = await signInWithPopup(auth, provider);
    setUser(result.user);
  };

  const handleLogout = async () => {
    await signOut(auth);
    setUser(null);
  };

  return (
    <div>
      {user ? (
        <>
          <h2>Welcome, {user.displayName}</h2>
          <img src={user.photoURL} alt="Avatar" />
          <button onClick={handleLogout}>Logout</button>
        </>
      ) : (
        <button onClick={handleLogin}>Login with Google</button>
      )}
    </div>
  );
}
export default App;


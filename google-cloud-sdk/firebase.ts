import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyCkGEmW5_aDHOusy_pCMoJ87bn3asC1Clc",
  authDomain: "homestagr.firebaseapp.com",
  projectId: "homestagr",
  storageBucket: "homestagr.appspot.com", // Corrected
  messagingSenderId: "556657674063",
  appId: "1:556657674063:web:f9b3f6f9704a1c0922a73a",
  measurementId: "G-8SWK7YW1TR"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();
const db = getFirestore(app);

export { app, auth, provider, db };


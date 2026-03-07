import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, GithubAuthProvider } from 'firebase/auth';

const firebaseConfig = {
    apiKey: "AIzaSyA7dPpQO5Xp679NmdQmxY0TKJJlUr9O7xE",
    authDomain: "node-zero-synapse.firebaseapp.com",
    projectId: "node-zero-synapse",
    storageBucket: "node-zero-synapse.firebasestorage.app",
    messagingSenderId: "1093694561290",
    appId: "1:1093694561290:web:94914de47c8c5cd17853f3",
    measurementId: "G-KW31QSC2MT",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
export const githubProvider = new GithubAuthProvider();

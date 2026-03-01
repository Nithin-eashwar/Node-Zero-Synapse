import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

export default function AppShell() {
    return (
        <div className="flex min-h-screen bg-black">
            {/* Fixed Sidebar */}
            <Sidebar />

            {/* Main Content Area */}
            <div className="ml-16 flex flex-1 flex-col">
                {/* Fixed Header */}
                <Header />

                {/* Page Content (scrollable) */}
                <main className="mt-14 flex-1 overflow-y-auto p-6">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}

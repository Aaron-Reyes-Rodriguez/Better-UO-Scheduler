import { Outlet } from 'react-router-dom';
import Navbar from './pages/components/navbar';

export default function Layout() {
    return (
        <div>
            <Navbar />
            <main>
                <Outlet />
            </main>
        </div>
    );
}

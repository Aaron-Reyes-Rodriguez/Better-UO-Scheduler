import { Outlet } from 'react-router-dom';
import Navbar from './pages/components/navbar';
import Box from '@mui/material/Box';

export default function Layout() {
    return (
        <Box 
            sx={{ 
                position: 'absolute', 
                top: 0, 
                left: 0, 
                right: 0, 
                minHeight: '100vh',
                display: 'flex',
                flexDirection: 'column'
            }}
        >
            <Navbar />
            <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
                <Outlet />
            </Box>
        </Box>
    );
}

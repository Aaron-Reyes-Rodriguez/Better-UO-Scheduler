import { Link } from 'react-router-dom';

export default function Navbar() {
    return (
        <nav className="bg-gray-800 p-4">
            <div className="container mx-auto">
                <div className="flex justify-between items-center">
                    <Link to="/" className="text-white text-2xl font-bold">Quackademics</Link>
                    <div className="flex space-x-4">
                        <Link to="/search" className="text-gray-300 hover:text-white">Search</Link>
                    </div>
                    <div>
                        <Link to="/scheduler" className="text-gray-300 hover:text-white">Transcript Parser</Link>
                    </div>
                </div>
            </div>
        </nav>
    );
}
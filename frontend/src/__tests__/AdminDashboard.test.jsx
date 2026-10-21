import { vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../lib/auth';
import AdminDashboard from '../cra-pages/AdminDashboard';

// Mock auth context
vi.mock('../lib/auth', async () => ({
    ...(await vi.importActual('../lib/auth')),
    useAuth: () => ({ user: { role: 'admin', name: 'Admin User' }, loading: false }),
}));

// Mock the HierarchyTree component (tested separately)
vi.mock('../components/HierarchyTree', () => ({
    default: function MockHierarchyTree() {
        return <div data-testid="hierarchy-tree">Hierarchy Tree</div>;
    },
}));

describe('AdminDashboard', () => {
    const renderDashboard = () => {
        return render(
            <BrowserRouter>
                <AuthProvider>
                    <AdminDashboard />
                </AuthProvider>
            </BrowserRouter>
        );
    };

    test('renders dashboard with data-testid', () => {
        renderDashboard();
        expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument();
    });

    test('renders hierarchy heading', () => {
        renderDashboard();
        expect(screen.getByText(/Academic Hierarchy/i)).toBeInTheDocument();
    });

    test('renders hierarchy tree component', () => {
        renderDashboard();
        expect(screen.getByTestId('hierarchy-tree')).toBeInTheDocument();
    });
});
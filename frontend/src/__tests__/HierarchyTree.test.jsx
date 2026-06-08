import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import HierarchyTree from '../components/HierarchyTree';

// Mock the admin API
jest.mock('../lib/api', () => ({
    adminApi: {
        listInstitutions: jest.fn().mockResolvedValue([
            { id: 'i1', name: 'Test Institution', code: 'TI' }
        ]),
        listInstitutionYears: jest.fn().mockResolvedValue([]),
        listInstitutionBranches: jest.fn().mockResolvedValue([]),
    },
}));

describe('HierarchyTree', () => {
    test('renders loading state initially', () => {
        render(<HierarchyTree />);
        // Should show loading indicator
        expect(screen.getByTestId('hierarchy-tree')).toBeInTheDocument();
    });

    test('renders institution nodes after loading', async () => {
        render(<HierarchyTree />);
        await waitFor(() => {
            expect(screen.getByText('Test Institution')).toBeInTheDocument();
        });
    });

    test('calls listInstitutions on mount', async () => {
        const { adminApi } = require('../lib/api');
        render(<HierarchyTree />);
        await waitFor(() => {
            expect(adminApi.listInstitutions).toHaveBeenCalled();
        });
    });
});
"use client";

import { useTenant, type Tenant } from "@/contexts/tenant-context";
import { useState, useRef, useEffect } from "react";

/**
 * Tenant Switcher Component
 *
 * A dropdown component that allows users to switch between tenants.
 * Shows the current tenant and available tenants for switching.
 *
 * Features:
 * - Displays current tenant name and role
 * - Dropdown menu for tenant selection
 * - Loading state during switch
 * - Error handling
 * - Keyboard accessibility
 */

interface TenantSwitcherProps {
  /** Custom class name for styling */
  className?: string;
  /** Callback when tenant is switched */
  onTenantChange?: (tenant: Tenant) => void;
}

export function TenantSwitcher({
  className = "",
  onTenantChange,
}: TenantSwitcherProps) {
  const {
    currentTenant,
    availableTenants,
    isLoading,
    error,
    switchTenant,
  } = useTenant();

  const [isOpen, setIsOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close dropdown on escape key
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, []);

  const handleTenantSelect = async (tenant: Tenant) => {
    if (tenant.id === currentTenant?.id) {
      setIsOpen(false);
      return;
    }

    setSwitching(true);
    try {
      await switchTenant(tenant.id);
      onTenantChange?.(tenant);
      setIsOpen(false);
    } catch {
      // Error is handled by context
    } finally {
      setSwitching(false);
    }
  };

  // Don't render if only one tenant or no tenants
  if (availableTenants.length <= 1) {
    if (currentTenant) {
      return (
        <div className={`flex items-center space-x-2 ${className}`}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-100 text-purple-600 text-sm font-medium">
            {currentTenant.name.charAt(0).toUpperCase()}
          </div>
          <div className="text-sm">
            <p className="font-medium text-gray-900">{currentTenant.name}</p>
            {currentTenant.role && (
              <p className="text-xs text-gray-500 capitalize">
                {currentTenant.role}
              </p>
            )}
          </div>
        </div>
      );
    }
    return null;
  }

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading || switching}
        className="flex items-center space-x-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-left hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Select tenant"
      >
        {currentTenant ? (
          <>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-100 text-purple-600 text-sm font-medium">
              {currentTenant.name.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-900 truncate">
                {currentTenant.name}
              </p>
              {currentTenant.role && (
                <p className="text-xs text-gray-500 capitalize">
                  {currentTenant.role}
                </p>
              )}
            </div>
          </>
        ) : (
          <span className="text-sm text-gray-500">Select tenant</span>
        )}
        <svg
          className={`h-5 w-5 text-gray-400 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          className="absolute left-0 z-50 mt-2 w-64 origin-top-left rounded-lg bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
          role="listbox"
          aria-label="Available tenants"
        >
          <div className="py-1">
            <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Switch Tenant
            </div>

            {error && (
              <div className="px-3 py-2 text-sm text-red-600 bg-red-50">
                {error}
              </div>
            )}

            {availableTenants.map((tenant) => (
              <button
                key={tenant.id}
                type="button"
                onClick={() => handleTenantSelect(tenant)}
                disabled={switching}
                className={`flex w-full items-center space-x-3 px-3 py-2 text-left hover:bg-gray-50 disabled:opacity-50 ${
                  tenant.id === currentTenant?.id ? "bg-blue-50" : ""
                }`}
                role="option"
                aria-selected={tenant.id === currentTenant?.id}
              >
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-lg text-sm font-medium ${
                    tenant.id === currentTenant?.id
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {tenant.name.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {tenant.name}
                  </p>
                  {tenant.role && (
                    <p className="text-xs text-gray-500 capitalize">
                      {tenant.role}
                    </p>
                  )}
                </div>
                {tenant.id === currentTenant?.id && (
                  <svg
                    className="h-5 w-5 text-blue-600"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {switching && (
        <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-white/50">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        </div>
      )}
    </div>
  );
}

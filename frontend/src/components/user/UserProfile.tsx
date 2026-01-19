import { useEffect, useState, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { Shield, Key, LogOut, Camera, Pencil, Loader2 } from "lucide-react"
import axios from "axios"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

import { useAuthStore } from "@/store/auth-store"
import { toast } from "sonner"

interface UserProfileProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type ProfileForm = {
  fullName: string
  dateOfBirth: string
  gender: string
  country: string
  phoneNumber: string
}

type CountryData = {
  code: string
  country: string
  dial_code: string
}

// Country code to flag emoji mapping
const COUNTRY_FLAGS: { [key: string]: string } = {
  VN: "🇻🇳",
  US: "🇺🇸",
  JP: "🇯🇵",
  KR: "🇰🇷",
  CN: "🇨🇳",
  TW: "🇹🇼",
  HK: "🇭🇰",
  SG: "🇸🇬",
  TH: "🇹🇭",
  ID: "🇮🇩",
  MY: "🇲🇾",
  PH: "🇵🇭",
  IN: "🇮🇳",
  AU: "🇦🇺",
  GB: "🇬🇧",
  FR: "🇫🇷",
  DE: "🇩🇪",
  IT: "🇮🇹",
  ES: "🇪🇸",
  NL: "🇳🇱",
  RU: "🇷🇺",
  BR: "🇧🇷",
}

export function UserProfile({ open, onOpenChange }: UserProfileProps) {
  const navigate = useNavigate()
  const { user, logout, changePassword, updateProfile } = useAuthStore()

  // ===== Derived =====
  const fullName = user?.fullName || "Anonymous User"
  const email = user?.email || "unknown@email.com"

  // ===== Edit mode =====
  const [isEditing, setIsEditing] = useState(false)

  // ===== Dialog states =====
  const [showChangePassword, setShowChangePassword] = useState(false)
  const [showPrivacySettings, setShowPrivacySettings] = useState(false)

  // ===== Countries data =====
  const [countries, setCountries] = useState<CountryData[]>([])
  const [loadingCountries, setLoadingCountries] = useState(false)

  // ===== Profile form =====
  const [profileForm, setProfileForm] = useState<ProfileForm>({
    fullName: user?.fullName || "",
    dateOfBirth: user?.dateOfBirth || "",
    gender: user?.gender || "",
    country: user?.country || "",
    phoneNumber: user?.phoneNumber || "",
  })

  // ===== Password form =====
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")

  // ===== Fetch countries =====
  useEffect(() => {
    const fetchCountries = async () => {
      try {
        setLoadingCountries(true)
        const response = await axios.get<CountryData[]>(
          "http://localhost:8000/api/meta/phone-countries"
        )
        setCountries(response.data)
      } catch (err) {
        console.error("Failed to fetch countries:", err)
      } finally {
        setLoadingCountries(false)
      }
    }

    fetchCountries()
  }, [])

  // ===== Selected country =====
  const selectedCountry = useMemo(() => {
    if (!profileForm.country) return null
    const country = countries.find(c => c.code === profileForm.country)
    if (!country) return null
    return {
      ...country,
      flag: COUNTRY_FLAGS[country.code] || "🌍",
    }
  }, [profileForm.country, countries])

  // ===== Country list with flags =====
  const countryList = useMemo(() => {
    return countries.map(country => ({
      ...country,
      flag: COUNTRY_FLAGS[country.code] || "🌍",
    }))
  }, [countries])

  // ===== Sync user → form =====
  useEffect(() => {
    if (!user) return
    setProfileForm({
      fullName: user.fullName || "",
      dateOfBirth: user.dateOfBirth || "",
      gender: user.gender || "",
      country: user.country || "",
      phoneNumber: user.phoneNumber || "",
    })
  }, [user])

  const onProfileChange = (
    key: keyof ProfileForm,
    value: string
  ) => {
    setProfileForm((prev) => ({ ...prev, [key]: value }))
  }

  // ===== Handlers =====
  const handleSaveProfile = async () => {
    try {
      const res = await updateProfile(
        profileForm.fullName,
        profileForm.dateOfBirth,
        profileForm.gender,
        profileForm.country,
        profileForm.phoneNumber,
      )

      if (res.success) {
        toast.success("Profile updated successfully")
        setIsEditing(false)
      } else {
        toast.error(res.message)
      }
    } catch {
      toast.error("Failed to update profile")
    }
  }

  const handleChangePassword = async () => {
    const res = await changePassword(
      currentPassword,
      newPassword,
      confirmPassword
    )

    if (res.success) {
      toast.success(res.message)
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      setShowChangePassword(false)
    } else {
      toast.error(res.message)
    }
  }

  const handleLogout = async () => {
    await logout()
    onOpenChange(false)
    navigate("/login")
  }

  const avatarFallback = fullName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase()

  return (
    <>
      {/* ================= PROFILE ================= */}
      <Dialog
        open={open && !showChangePassword && !showPrivacySettings}
        onOpenChange={onOpenChange}
      >
        <DialogContent className="sm:max-w-2xl max-h-[90vh] flex flex-col rounded-xl">
          <DialogHeader>
            <DialogTitle className="text-2xl">
              User Profile
            </DialogTitle>
            <DialogDescription>
              View and manage your personal information.
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto pr-2">
            {/* Avatar */}
            <div className="flex flex-col items-center gap-4 py-6">
              <div className="relative group">
                <Avatar className="h-24 w-24 border-4 border-primary/10 shadow-lg">
                  <AvatarImage src="/user-avatar.png" />
                  <AvatarFallback className="bg-primary text-white text-2xl font-bold">
                    {avatarFallback}
                  </AvatarFallback>
                </Avatar>
                <button
                  type="button"
                  className="absolute bottom-0 right-0 h-8 w-8 bg-primary rounded-full border-2 border-white shadow-md flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Camera className="h-4 w-4 text-white" />
                </button>
              </div>

              <div className="text-center">
                <h3 className="font-bold text-xl">{fullName}</h3>
                <p className="text-sm text-muted-foreground">
                  {email}
                </p>
              </div>
            </div>

            <Separator />

            {/* Profile form */}
            {loadingCountries ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-6">
                <div className="grid gap-2">
                  <Label>Full name</Label>
                  <Input
                    value={profileForm.fullName}
                    disabled={!isEditing}
                    onChange={(e) =>
                      onProfileChange("fullName", e.target.value)
                    }
                  />
                </div>

                <div className="grid gap-2">
                  <Label>Date of birth</Label>
                  <Input
                    type="date"
                    value={profileForm.dateOfBirth}
                    disabled={!isEditing}
                    onChange={(e) =>
                      onProfileChange("dateOfBirth", e.target.value)
                    }
                  />
                </div>

                <div className="grid gap-2">
                  <Label>Gender</Label>
                  <Select
                    value={profileForm.gender}
                    disabled={!isEditing}
                    onValueChange={(v) =>
                      onProfileChange("gender", v)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select gender" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male">Male</SelectItem>
                      <SelectItem value="female">Female</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label>Country / Region</Label>
                  <Select
                    value={profileForm.country}
                    disabled={!isEditing}
                    onValueChange={(v) => onProfileChange("country", v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select country" />
                    </SelectTrigger>
                    <SelectContent className="max-h-[300px]">
                      {countryList.map((country) => (
                        <SelectItem key={country.code} value={country.code}>
                          <div className="flex items-center gap-2">
                            <span className="text-xl">{country.flag}</span>
                            <span>{country.country}</span>
                            <span className="text-muted-foreground text-xs">
                              ({country.dial_code})
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2 md:col-span-2">
                  <Label>Phone number</Label>
                  <div className="flex gap-2">
                    <div className="w-28 shrink-0">
                      <Input
                        value={selectedCountry?.dial_code || "+84"}
                        disabled
                        className="bg-muted"
                      />
                    </div>
                    <Input
                      type="tel"
                      placeholder="912345678"
                      value={profileForm.phoneNumber}
                      disabled={!isEditing}
                      onChange={(e) => {
                        const dialCode = selectedCountry?.dial_code || "+84"
                        let value = e.target.value.replace(/\D/g, "")

                        if (value && !value.startsWith(dialCode.slice(1))) {
                          value = dialCode + value
                        } else if (value) {
                          value = "+" + value
                        }

                        onProfileChange("phoneNumber", value)
                      }}
                      className="flex-1"
                    />
                  </div>
                </div>
              </div>
            )}

            <Separator />

            {/* Actions */}
            <div className="flex flex-col gap-2 py-4">
              <Button
                variant="ghost"
                className="justify-start"
                onClick={() => {
                  onOpenChange(false)
                  setShowChangePassword(true)
                }}
              >
                <Key className="mr-2 h-4 w-4" />
                Change Password
              </Button>

              <Button
                variant="ghost"
                className="justify-start"
                onClick={() => {
                  onOpenChange(false)
                  setShowPrivacySettings(true)
                }}
              >
                <Shield className="mr-2 h-4 w-4" />
                Privacy Settings
              </Button>

              <Separator className="my-2" />

              <Button
                variant="ghost"
                className="justify-start text-red-600 hover:text-red-700 hover:bg-red-50"
                onClick={handleLogout}
              >
                <LogOut className="mr-2 h-4 w-4" />
                Log Out
              </Button>
            </div>
          </div>

          <DialogFooter>
            {!isEditing ? (
              <>
                <Button
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                >
                  Close
                </Button>
                <Button onClick={() => setIsEditing(true)}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Edit Profile
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={() => {
                    setIsEditing(false)
                    if (user) {
                      setProfileForm({
                        fullName: user.fullName || "",
                        dateOfBirth: user.dateOfBirth || "",
                        gender: user.gender || "",
                        country: user.country || "",
                        phoneNumber: user.phoneNumber || "",
                      })
                    }
                  }}
                >
                  Cancel
                </Button>
                <Button onClick={handleSaveProfile}>
                  Save Changes
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ================= CHANGE PASSWORD ================= */}
      <Dialog
        open={showChangePassword}
        onOpenChange={setShowChangePassword}
      >
        <DialogContent className="sm:max-w-md rounded-xl">
          <DialogHeader>
            <DialogTitle>Change Password</DialogTitle>
            <DialogDescription>
              Enter your current password and a new one.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Current Password</Label>
              <Input
                type="password"
                value={currentPassword}
                onChange={(e) =>
                  setCurrentPassword(e.target.value)
                }
              />
            </div>

            <div className="grid gap-2">
              <Label>New Password</Label>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) =>
                  setNewPassword(e.target.value)
                }
              />
            </div>

            <div className="grid gap-2">
              <Label>Confirm Password</Label>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) =>
                  setConfirmPassword(e.target.value)
                }
              />
              {confirmPassword &&
                newPassword !== confirmPassword && (
                  <p className="text-xs text-red-600">
                    Passwords do not match
                  </p>
                )}
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowChangePassword(false)
                setCurrentPassword("")
                setNewPassword("")
                setConfirmPassword("")
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleChangePassword}
              disabled={
                !currentPassword ||
                !newPassword ||
                newPassword !== confirmPassword
              }
            >
              Change Password
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ================= PRIVACY SETTINGS ================= */}
      <Dialog
        open={showPrivacySettings}
        onOpenChange={setShowPrivacySettings}
      >
        <DialogContent className="sm:max-w-lg rounded-xl">
          <DialogHeader>
            <DialogTitle>Privacy Settings</DialogTitle>
            <DialogDescription>
              Manage your privacy preferences.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="flex justify-between border p-3 rounded-lg">
              <span>Profile Visibility</span>
              <Button size="sm" variant="outline">
                Public
              </Button>
            </div>

            <div className="flex justify-between border p-3 rounded-lg">
              <span>Activity Status</span>
              <Button size="sm" variant="outline">
                Enabled
              </Button>
            </div>
          </div>

          <DialogFooter>
            <Button onClick={() => setShowPrivacySettings(false)}>
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

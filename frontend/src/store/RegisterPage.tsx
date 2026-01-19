import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { UserPlus, Loader2 } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { useState, useMemo, useEffect } from "react"
import { toast } from "sonner"
import { useAuthStore } from "@/store/auth-store"
import axios from "axios"

type RegisterForm = {
  username: string
  email: string
  fullName: string
  dateOfBirth: string
  gender: string
  country: string
  phoneNumber: string
  password: string
  confirmPassword: string
}

type CountryData = {
  code: string
  country: string
  dial_code: string
}

type PhoneNumberSupport = CountryData[]

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

export default function RegisterPage() {
  const navigate = useNavigate()
  const register = useAuthStore((state) => state.register)

  const [form, setForm] = useState<RegisterForm>({
    username: "",
    email: "",
    fullName: "",
    dateOfBirth: "",
    gender: "",
    country: "VN",
    phoneNumber: "",
    password: "",
    confirmPassword: "",
  })

  const [error, setError] = useState("")
  const [countries, setCountries] = useState<PhoneNumberSupport>([])
  const [loadingCountries, setLoadingCountries] = useState(true)

  // Fetch countries from API
  useEffect(() => {
    const fetchCountries = async () => {
      try {
        const response = await axios.get<PhoneNumberSupport>(
          "http://localhost:8000/api/meta/phone-countries"
        )
        setCountries(response.data)
        setLoadingCountries(false)
      } catch (err) {
        console.error("Failed to fetch countries:", err)
        toast.error("Failed to load country list")
        setLoadingCountries(false)
      }
    }

    fetchCountries()
  }, [])

  // Lấy thông tin country được chọn
  const selectedCountry = useMemo(() => {
    if (!form.country) return null
    const country = countries.find(c => c.code === form.country)
    if (!country) return null
    return {
      ...country,
      flag: COUNTRY_FLAGS[country.code] || "🌍",
    }
  }, [form.country, countries])

  // Country list đã có sẵn từ API (array)
  const countryList = useMemo(() => {
    return countries.map(country => ({
      ...country,
      flag: COUNTRY_FLAGS[country.code] || "🌍",
    }))
  }, [countries])

  const onChange = (key: keyof RegisterForm, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match")
      return
    }

    // Validate phone number format
    if (form.phoneNumber && !form.phoneNumber.startsWith("+")) {
      setError("Phone number must include country code")
      return
    }

    try {
      const success = await register(
        form.username,
        form.email,
        form.fullName,
        form.dateOfBirth,
        form.gender,
        form.country,
        form.phoneNumber,
        form.password,
        form.confirmPassword
      )

      if (success) {
        toast.success("Register successful")
        navigate("/login", { replace: true })
      } else {
        toast.error("Register failed")
        setError("Register failed. Please try again.")
      }
    } catch (err) {
      toast.error("Register failed")
      setError("Register failed. Please try again.")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/5 via-white to-primary/10 p-4">
      <Card className="w-full max-w-2xl shadow-2xl rounded-2xl">
        <CardHeader className="space-y-4 pb-8 text-center">
          <div className="mx-auto h-16 w-16 rounded-2xl bg-tech-gradient flex items-center justify-center shadow-lg">
            <UserPlus className="h-10 w-10 text-white" />
          </div>

          <CardTitle className="text-3xl font-bold text-primary">
            Create Account
          </CardTitle>
          <CardDescription>MultiAgentX Enterprise AI</CardDescription>
        </CardHeader>

        <CardContent className="max-h-[70vh] overflow-y-auto pr-2 scroll-smooth">
          {loadingCountries ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <Label>Username</Label>
                <Input
                  value={form.username}
                  onChange={(e) => onChange("username", e.target.value)}
                  required
                />
              </div>

              <div>
                <Label>Email</Label>
                <Input
                  type="email"
                  value={form.email}
                  onChange={(e) => onChange("email", e.target.value)}
                  required
                />
              </div>

              <div>
                <Label>Full name</Label>
                <Input
                  value={form.fullName}
                  onChange={(e) => onChange("fullName", e.target.value)}
                  required
                />
              </div>

              <div>
                <Label>Date of birth</Label>
                <Input
                  type="date"
                  value={form.dateOfBirth}
                  onChange={(e) => onChange("dateOfBirth", e.target.value)}
                  required
                />
              </div>

              <div>
                <Label>Gender</Label>
                <Select
                  value={form.gender}
                  onValueChange={(v) => onChange("gender", v)}
                  required
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

              <div>
                <Label>Country / Region</Label>
                <Select
                  value={form.country}
                  onValueChange={(v) => onChange("country", v)}
                  required
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
                {selectedCountry && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Selected: {selectedCountry.flag} {selectedCountry.country}
                  </p>
                )}
              </div>

              <div>
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
                    value={form.phoneNumber}
                    onChange={(e) => {
                      const dialCode = selectedCountry?.dial_code || "+84"
                      let value = e.target.value.replace(/\D/g, "")

                      if (value && !value.startsWith(dialCode.slice(1))) {
                        value = dialCode + value
                      } else if (value) {
                        value = "+" + value
                      }

                      onChange("phoneNumber", value)
                    }}
                    required
                    className="flex-1"
                  />
                </div>
                {selectedCountry && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Example: {selectedCountry.dial_code}912345678
                  </p>
                )}
              </div>

              <div>
                <Label>Password</Label>
                <Input
                  type="password"
                  value={form.password}
                  onChange={(e) => onChange("password", e.target.value)}
                  required
                  minLength={8}
                />
              </div>

              <div>
                <Label>Confirm password</Label>
                <Input
                  type="password"
                  value={form.confirmPassword}
                  onChange={(e) => onChange("confirmPassword", e.target.value)}
                  required
                />
                {form.confirmPassword &&
                  form.password !== form.confirmPassword && (
                    <p className="text-xs text-red-600 mt-1">
                      Passwords do not match
                    </p>
                  )}
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}

              <Button type="submit" className="w-full h-11">
                Sign Up
              </Button>

              <div className="text-center text-sm text-muted-foreground">
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => navigate("/login")}
                  className="text-primary font-medium hover:underline"
                >
                  Sign in
                </button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

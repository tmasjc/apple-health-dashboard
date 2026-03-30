import { useState } from "react";
import type { Profile } from "../api/types";

interface Props {
  profile: Profile;
  onSave: (p: Profile) => void;
  onClose: () => void;
}

export default function ProfileModal({ profile, onSave, onClose }: Props) {
  const [name, setName] = useState(profile.display_name);
  const [gender, setGender] = useState<Profile["gender"]>(profile.gender);

  const handleSave = () => {
    onSave({ display_name: name, gender });
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2 style={{ marginBottom: 16 }}>Profile Settings</h2>

        <label className="modal-label">
          Display Name
          <input
            className="modal-input"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
          />
        </label>

        <fieldset className="modal-fieldset">
          <legend className="modal-label">Gender</legend>
          <label className="modal-radio">
            <input
              type="radio"
              name="gender"
              checked={gender === "male"}
              onChange={() => setGender("male")}
            />
            Male
          </label>
          <label className="modal-radio">
            <input
              type="radio"
              name="gender"
              checked={gender === "female"}
              onChange={() => setGender("female")}
            />
            Female
          </label>
        </fieldset>

        <div style={{ display: "flex", gap: 8, marginTop: 20, justifyContent: "flex-end" }}>
          <button className="modal-btn modal-btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="modal-btn modal-btn-primary" onClick={handleSave}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

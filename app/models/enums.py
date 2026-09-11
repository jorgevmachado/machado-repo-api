from enum import Enum

class GenderEnum(str, Enum):
    MALE = 'MALE'
    FEMALE = 'FEMALE'
    OTHER = 'OTHER'

class StatusEnum(str, Enum):
    ACTIVE = 'ACTIVE'    
    INACTIVE = 'INACTIVE'    

class RoleEnum(str, Enum):
    USER = 'USER'    
    ADMIN = 'ADMIN'    
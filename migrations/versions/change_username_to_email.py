"""change_username_to_email

Revision ID: change_username_to_email
Revises: 109c3ea32a1b
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'change_username_to_email'
down_revision: Union[str, Sequence[str], None] = '109c3ea32a1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - rename username to email and convert existing usernames to email format."""
    # Önce email sütununu ekle (eğer yoksa)
    conn = op.get_bind()
    
    # Mevcut sütunları kontrol et
    inspector = sa.inspect(conn)
    user_columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'username' in user_columns and 'email' not in user_columns:
        # username sütununu email'e çevir
        # Önce index'i kaldır
        op.drop_index('ix_users_username', table_name='users')
        
        # Mevcut username değerlerini email formatına çevir
        # Eğer zaten @ işareti varsa olduğu gibi bırak, yoksa @gmail.com ekle
        conn.execute(sa.text("""
            UPDATE users 
            SET username = CASE 
                WHEN username LIKE '%@%' THEN username 
                ELSE username || '@gmail.com' 
            END
        """))
        
        # Sütunu yeniden adlandır
        op.alter_column('users', 'username', new_column_name='email', type_=sa.String(length=255))
        
        # Yeni index oluştur
        op.create_index('ix_users_email', 'users', ['email'], unique=True)
    elif 'username' in user_columns and 'email' in user_columns:
        # Her iki sütun da varsa, username'deki değerleri email'e kopyala ve username'i sil
        conn.execute(sa.text("""
            UPDATE users 
            SET email = CASE 
                WHEN username LIKE '%@%' THEN username 
                ELSE username || '@gmail.com' 
            END
            WHERE email IS NULL OR email = ''
        """))
        op.drop_index('ix_users_username', table_name='users')
        op.drop_column('users', 'username')
    elif 'email' not in user_columns:
        # Sadece username varsa ve email yoksa
        op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
        conn.execute(sa.text("""
            UPDATE users 
            SET email = CASE 
                WHEN username LIKE '%@%' THEN username 
                ELSE username || '@gmail.com' 
            END
        """))
        op.alter_column('users', 'email', nullable=False)
        op.drop_index('ix_users_username', table_name='users')
        op.drop_column('users', 'username')
        op.create_index('ix_users_email', 'users', ['email'], unique=True)


def downgrade() -> None:
    """Downgrade schema - rename email back to username."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'email' in user_columns:
        op.drop_index('ix_users_email', table_name='users')
        op.alter_column('users', 'email', new_column_name='username', type_=sa.String(length=50))
        op.create_index('ix_users_username', 'users', ['username'], unique=True)


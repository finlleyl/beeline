# from sqlalchemy import delete, insert, select


# class BaseDAO:
#     model = None

#     @classmethod
#     async def add(cls, session=None, **data):

#         if session is not None:
#             query = insert(cls.model).values(**data).returning(cls.model.id)
#             result = await session.execute(query)
#             return result.scalar_one()

#         async with async_session_maker() as session:
#             query = insert(cls.model).values(**data).returning(cls.model.id)
#             result = await session.execute(query)
#             await session.commit()
#             return result.scalar_one()
